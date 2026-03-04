import asyncio

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from browser import create_browser
from sites.springer.scrape import get_page_count, scrape_page

app = FastAPI(title="Scrapper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic-модели запросов и ответов ---


class ScrapeRequest(BaseModel):
    query: str
    page_from: int = 1
    page_to: int = 1
    only_full_access: bool = True


class Article(BaseModel):
    title: str
    description: str
    authors: str


class ScrapeResponse(BaseModel):
    articles: list[Article]
    total: int
    skipped: int


class PageCountResponse(BaseModel):
    total_pages: int


# --- Эндпоинты ---


@app.get("/api/springer/page-count", response_model=PageCountResponse)
async def springer_page_count(query: str = Query(..., min_length=1)):
    """
    Получить количество страниц результатов поиска на SpringerLink.
    Запускает браузер, открывает поиск, парсит пагинацию.
    """
    def _fetch():
        driver = create_browser()
        try:
            return get_page_count(driver, query)
        finally:
            driver.quit()

    total = await asyncio.to_thread(_fetch)
    return PageCountResponse(total_pages=total)


@app.post("/api/springer/scrape", response_model=ScrapeResponse)
async def springer_scrape(body: ScrapeRequest):
    """
    Скрапить статьи со страниц результатов поиска SpringerLink.
    Обходит страницы от page_from до page_to, собирает статьи.
    """
    def _fetch():
        driver = create_browser()
        try:
            all_articles = []
            total_skipped = 0
            for page_num in range(body.page_from, body.page_to + 1):
                result = scrape_page(
                    driver, body.query, page_num, body.only_full_access
                )
                all_articles.extend(result["articles"])
                total_skipped += result["skipped"]
            return all_articles, total_skipped
        finally:
            driver.quit()

    articles, skipped = await asyncio.to_thread(_fetch)
    return ScrapeResponse(
        articles=articles,
        total=len(articles),
        skipped=skipped,
    )
