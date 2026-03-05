import asyncio
import json
import logging
import threading
import time
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from config import DELAY_BETWEEN_PAGES
from browser import create_browser
from sites.springer.scrape import get_page_count, get_page_count_fast, scrape_page, scrape_abstract, scrape_full_article
from database import (
    init_db, create_session, insert_articles, get_article,
    update_article_abstract, get_all_sessions, delete_session,
    get_session, search_articles_by_title, update_session_pages,
    insert_article_sections, insert_article_references,
    get_article_sections, get_article_references, is_article_analyzed,
)

app = FastAPI(title="Scrapper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

active_scrapes: dict[int, threading.Event] = {}


def _sse_event(event_type: str, data: dict) -> str:
    payload = {**data, "type": event_type}
    return f"data: {json.dumps(payload)}\n\n"


# --- Pydantic-модели запросов и ответов ---


class ScrapeRequest(BaseModel):
    query: str
    page_from: int = 1
    page_to: int = 1
    only_full_access: bool = True
    date_from: str = ""
    date_to: str = ""


class Article(BaseModel):
    id: Optional[int] = None
    title: str
    url: str = ""
    published_date: str = ""
    description: str = ""
    authors: str = ""
    abstract: Optional[str] = None


class ScrapeResponse(BaseModel):
    session_id: int
    articles: list[Article]
    total: int
    skipped: int


class PageCountResponse(BaseModel):
    total_pages: int


class AbstractResponse(BaseModel):
    abstract: str


class SectionItem(BaseModel):
    id: int
    title: str
    content: str
    heading_level: int
    order_index: int


class ReferenceItem(BaseModel):
    id: int
    ref_number: int
    text: str
    doi: str


class ArticleFullResponse(BaseModel):
    id: int
    title: str
    url: str
    published_date: str
    authors: str
    abstract: Optional[str]
    sections: list[SectionItem]
    references: list[ReferenceItem]


class SessionListItem(BaseModel):
    id: int
    query: str
    created_at: str
    article_count: int
    pages_scanned: int


class SessionDetailResponse(BaseModel):
    id: int
    query: str
    created_at: str
    articles: list[Article]


# --- Эндпоинты ---


@app.get("/api/springer/page-count", response_model=PageCountResponse)
async def springer_page_count(
    query: str = Query(..., min_length=1),
    only_full_access: bool = Query(False),
    date_from: str = Query(""),
    date_to: str = Query(""),
):
    try:
        total = await asyncio.to_thread(
            get_page_count_fast, query, only_full_access, date_from, date_to
        )
        return PageCountResponse(total_pages=total)
    except Exception as fast_err:
        logger.warning("Fast page-count failed (%s), falling back to Selenium", fast_err)

    def _fetch_selenium():
        driver = create_browser()
        try:
            return get_page_count(driver, query, only_full_access, date_from, date_to)
        finally:
            driver.quit()

    try:
        total = await asyncio.to_thread(_fetch_selenium)
    except Exception as e:
        logger.exception("page-count failed (both fast and Selenium)")
        raise HTTPException(status_code=500, detail=str(e))
    return PageCountResponse(total_pages=total)


@app.get("/api/springer/scrape")
async def springer_scrape_sse(
    query: str = Query(..., min_length=1),
    page_from: int = Query(1),
    page_to: int = Query(1),
    only_full_access: bool = Query(True),
    date_from: str = Query(""),
    date_to: str = Query(""),
):
    session_id = create_session(query)
    stop_event = threading.Event()
    active_scrapes[session_id] = stop_event

    async def event_generator():
        total_articles = 0
        total_skipped = 0
        try:
            yield _sse_event("started", {"session_id": session_id})

            driver = create_browser()
            try:
                total_pages = page_to - page_from + 1
                for page_num in range(page_from, page_to + 1):
                    if stop_event.is_set():
                        yield _sse_event("stopped", {
                            "session_id": session_id,
                            "total": total_articles,
                            "skipped": total_skipped,
                        })
                        return

                    try:
                        result = await asyncio.to_thread(
                            scrape_page, driver, query, page_num,
                            only_full_access, date_from, date_to,
                        )
                    except Exception as page_err:
                        logger.warning("Page %d failed: %s", page_num, page_err)
                        pages_done = page_num - page_from + 1
                        update_session_pages(session_id, pages_done)
                        yield _sse_event("progress", {
                            "current_page": pages_done,
                            "total_pages": total_pages,
                            "articles_found": total_articles,
                            "skipped": total_skipped,
                            "page_error": f"Страница {page_num} пропущена",
                        })
                        continue

                    page_articles = result["articles"]
                    if page_articles:
                        insert_articles(session_id, page_articles)
                    total_articles += len(page_articles)
                    total_skipped += result["skipped"]
                    pages_done = page_num - page_from + 1
                    update_session_pages(session_id, pages_done)

                    yield _sse_event("progress", {
                        "current_page": pages_done,
                        "total_pages": total_pages,
                        "articles_found": total_articles,
                        "skipped": total_skipped,
                    })

                    if page_num < page_to and DELAY_BETWEEN_PAGES > 0:
                        await asyncio.sleep(DELAY_BETWEEN_PAGES)

                yield _sse_event("complete", {
                    "session_id": session_id,
                    "total": total_articles,
                    "skipped": total_skipped,
                })
            finally:
                driver.quit()
        except Exception as e:
            logger.exception("scrape SSE failed")
            yield _sse_event("error", {"message": str(e)})
        finally:
            active_scrapes.pop(session_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/springer/scrape/{session_id}/stop")
async def stop_scrape(session_id: int):
    event = active_scrapes.get(session_id)
    if not event:
        raise HTTPException(404, "Scrape not found or already completed")
    event.set()
    return {"ok": True}


@app.post("/api/springer/article/{article_id}/abstract", response_model=AbstractResponse)
async def fetch_article_abstract(article_id: int):
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.get("abstract") and is_article_analyzed(article_id):
        return AbstractResponse(abstract=article["abstract"])

    article_url = article["url"]
    if not article_url:
        raise HTTPException(status_code=400, detail="Article has no URL")

    def _fetch():
        driver = create_browser()
        try:
            return scrape_full_article(driver, article_url)
        finally:
            driver.quit()

    try:
        result = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.exception("full article scrape failed for article %s", article_id)
        raise HTTPException(status_code=500, detail=str(e))

    update_article_abstract(article_id, result["abstract"])

    if result["sections"]:
        insert_article_sections(article_id, result["sections"])
    if result["references"]:
        insert_article_references(article_id, result["references"])

    return AbstractResponse(abstract=result["abstract"])


@app.get("/api/article/{article_id}/full", response_model=ArticleFullResponse)
async def get_full_article(article_id: int):
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    sections = get_article_sections(article_id)
    references = get_article_references(article_id)

    return ArticleFullResponse(
        id=article["id"],
        title=article["title"],
        url=article.get("url", ""),
        published_date=article.get("published_date", ""),
        authors=article.get("authors", ""),
        abstract=article.get("abstract"),
        sections=[SectionItem(**s) for s in sections],
        references=[ReferenceItem(**r) for r in references],
    )


@app.get("/api/sessions", response_model=list[SessionListItem])
async def list_sessions():
    return get_all_sessions()


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: int):
    if not delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@app.get("/api/sessions/{session_id}", response_model=SessionDetailResponse)
async def session_detail(session_id: int, search: str = Query("")):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    articles = search_articles_by_title(session_id, search)
    return SessionDetailResponse(
        id=session["id"],
        query=session["query"],
        created_at=session["created_at"],
        articles=[Article(
            id=a["id"],
            title=a["title"],
            url=a.get("url", ""),
            published_date=a.get("published_date", ""),
            description=a.get("description", ""),
            authors=a.get("authors", ""),
            abstract=a.get("abstract"),
        ) for a in articles],
    )
