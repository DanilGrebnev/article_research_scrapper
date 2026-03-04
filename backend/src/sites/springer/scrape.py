from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from scraper import Scraper

# Базовый URL сайта SpringerLink
BASE_URL = "https://link.springer.com"


def get_page_count(driver: WebDriver, query: str) -> int:
    """
    Открывает страницу поиска SpringerLink и возвращает
    общее количество страниц результатов.
    """
    scraper = Scraper(driver)

    # Формируем URL поиска и открываем страницу
    search_url = f"{BASE_URL}/search?query={quote_plus(query)}"
    scraper.go_to(search_url)

    # Ждём загрузки хотя бы одного заголовка статьи
    scraper.wait_for('[data-test="title"]', timeout=20)

    # Извлекаем номера страниц из пагинации:
    # каждый <li> с атрибутом data-page содержит номер страницы
    page_items = driver.find_elements(
        By.CSS_SELECTOR, "li.eds-c-pagination__item[data-page]"
    )
    if not page_items:
        return 1

    max_page = max(int(item.get_attribute("data-page")) for item in page_items)
    return max_page


def scrape_page(
    driver: WebDriver,
    query: str,
    page: int = 1,
    only_full_access: bool = True,
) -> dict:
    """
    Скрапит одну страницу результатов поиска SpringerLink.

    Возвращает словарь:
      - articles: список статей [{title, description, authors}, ...]
      - skipped: количество пропущенных статей (без полного доступа)
    """
    scraper = Scraper(driver)

    # Формируем URL с номером страницы
    search_url = f"{BASE_URL}/search?query={quote_plus(query)}&page={page}"
    scraper.go_to(search_url)

    # Ждём загрузки результатов
    scraper.wait_for('[data-test="title"]', timeout=20)

    # Находим все карточки статей на странице
    # Каждая карточка — div.app-card-open__main
    cards = driver.find_elements(By.CSS_SELECTOR, "div.app-card-open__main")

    articles = []
    skipped = 0

    for card in cards:
        # --- Проверка доступа к статье ---
        # У статей с полным доступом есть элемент [data-test="entitlements"]
        # с текстом "Full access". У статей без полного доступа его нет.
        entitlement_els = card.find_elements(
            By.CSS_SELECTOR, '[data-test="entitlements"]'
        )
        has_full_access = (
            entitlement_els
            and "full access" in entitlement_els[0].text.strip().lower()
        )
        if only_full_access and not has_full_access:
            skipped += 1
            continue

        # --- Заголовок: <h3 data-test="title"> -> <span> ---
        title_els = card.find_elements(
            By.CSS_SELECTOR, 'h3[data-test="title"] span'
        )
        title = title_els[0].text.strip() if title_els else "—"

        # --- Описание: <div data-test="description"> -> <p> ---
        desc_els = card.find_elements(
            By.CSS_SELECTOR, '[data-test="description"] p'
        )
        description = desc_els[0].text.strip() if desc_els else "—"

        # --- Авторы: <span data-test="authors"> ---
        author_els = card.find_elements(
            By.CSS_SELECTOR, '[data-test="authors"]'
        )
        authors = author_els[0].text.strip() if author_els else "—"

        articles.append({
            "title": title,
            "description": description,
            "authors": authors,
        })

    return {"articles": articles, "skipped": skipped}
