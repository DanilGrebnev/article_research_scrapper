import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from browser import create_browser
from sites.springer.scrape import get_page_count, scrape_page, scrape_abstract
from database import init_db, create_session, insert_articles, get_article, update_article_abstract

app = FastAPI(title="Scrapper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


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


# --- Эндпоинты ---


@app.get("/api/springer/page-count", response_model=PageCountResponse)
async def springer_page_count(
    query: str = Query(..., min_length=1),
    only_full_access: bool = Query(False),
    date_from: str = Query(""),
    date_to: str = Query(""),
):
    def _fetch():
        driver = create_browser()
        try:
            return get_page_count(driver, query, only_full_access, date_from, date_to)
        finally:
            driver.quit()

    try:
        total = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.exception("page-count failed")
        raise HTTPException(status_code=500, detail=str(e))
    return PageCountResponse(total_pages=total)


@app.post("/api/springer/scrape", response_model=ScrapeResponse)
async def springer_scrape(body: ScrapeRequest):
    def _fetch():
        driver = create_browser()
        try:
            all_articles = []
            total_skipped = 0
            for page_num in range(body.page_from, body.page_to + 1):
                result = scrape_page(
                    driver, body.query, page_num, body.only_full_access,
                    body.date_from, body.date_to,
                )
                all_articles.extend(result["articles"])
                total_skipped += result["skipped"]
            return all_articles, total_skipped
        finally:
            driver.quit()

    try:
        articles, skipped = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.exception("scrape failed")
        raise HTTPException(status_code=500, detail=str(e))

    session_id = create_session(body.query)
    article_ids = insert_articles(session_id, articles)

    response_articles = []
    for art, art_id in zip(articles, article_ids):
        response_articles.append(Article(
            id=art_id,
            title=art["title"],
            url=art.get("url", ""),
            published_date=art.get("published_date", ""),
            description=art.get("description", ""),
            authors=art.get("authors", ""),
        ))

    return ScrapeResponse(
        session_id=session_id,
        articles=response_articles,
        total=len(response_articles),
        skipped=skipped,
    )


@app.post("/api/springer/article/{article_id}/abstract", response_model=AbstractResponse)
async def fetch_article_abstract(article_id: int):
    article = get_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if article.get("abstract"):
        return AbstractResponse(abstract=article["abstract"])

    article_url = article["url"]
    if not article_url:
        raise HTTPException(status_code=400, detail="Article has no URL")

    def _fetch():
        driver = create_browser()
        try:
            return scrape_abstract(driver, article_url)
        finally:
            driver.quit()

    try:
        abstract = await asyncio.to_thread(_fetch)
    except Exception as e:
        logger.exception("abstract scrape failed for article %s", article_id)
        raise HTTPException(status_code=500, detail=str(e))

    update_article_abstract(article_id, abstract)
    return AbstractResponse(abstract=abstract)
