import logging
import time
from urllib.parse import quote_plus

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from config import (
    WAIT_TIMEOUT, PAGE_LOAD_TIMEOUT, ABSTRACT_LOAD_TIMEOUT,
    DELAY_AFTER_COOKIE, PAGE_LOAD_RETRIES,
    RETRY_DELAY_BASE, RETRY_DELAY_STEP,
    CHALLENGE_DELAY_BASE, CHALLENGE_DELAY_STEP,
)
from scraper import Scraper

logger = logging.getLogger(__name__)

BASE_URL = "https://link.springer.com"


def _dismiss_cookie_consent(driver: WebDriver):
    """Close Springer's cookie consent dialog if present."""
    try:
        driver.implicitly_wait(0)
        buttons = driver.find_elements(
            By.CSS_SELECTOR, "button[data-cc-action='accept']"
        )
        if buttons:
            buttons[0].click()
            time.sleep(DELAY_AFTER_COOKIE)
    except Exception:
        pass
    finally:
        driver.implicitly_wait(WAIT_TIMEOUT)


def _is_client_challenge(driver: WebDriver) -> bool:
    """Check if Springer is showing a bot-protection 'Client Challenge' page."""
    try:
        return "Client Challenge" in driver.title or bool(
            driver.find_elements(By.CSS_SELECTOR, "div.challenge-container, #challenge-running")
        )
    except Exception:
        return False


def _navigate_and_wait(driver: WebDriver, url: str, retries: int = PAGE_LOAD_RETRIES):
    """Navigate to URL and wait for results, with retry and consent/challenge handling."""
    scraper = Scraper(driver)
    last_err = None
    for attempt in range(retries + 1):
        try:
            scraper.go_to(url)
            _dismiss_cookie_consent(driver)

            if _is_client_challenge(driver):
                logger.warning("Client Challenge detected (attempt %d), waiting...", attempt + 1)
                time.sleep(CHALLENGE_DELAY_BASE + attempt * CHALLENGE_DELAY_STEP)
                scraper.go_to(url)
                _dismiss_cookie_consent(driver)

            scraper.wait_for('[data-test="title"]', timeout=PAGE_LOAD_TIMEOUT)
            return
        except (TimeoutException, WebDriverException) as e:
            last_err = e
            logger.warning("Page load attempt %d failed for %s: %s", attempt + 1, url, e.__class__.__name__)
            time.sleep(RETRY_DELAY_BASE + attempt * RETRY_DELAY_STEP)
    raise last_err


def _build_search_url(
    query: str,
    page: int = 1,
    open_access: bool = False,
    date_from: str = "",
    date_to: str = "",
) -> str:
    url = f"{BASE_URL}/search?query={quote_plus(query)}&sortBy=relevance&page={page}"
    if open_access:
        url += "&openAccess=true"
    if date_from or date_to:
        url += f"&date=custom&dateFrom={date_from}&dateTo={date_to}"
    return url


def get_page_count(
    driver: WebDriver,
    query: str,
    only_full_access: bool = False,
    date_from: str = "",
    date_to: str = "",
) -> int:
    """
    Открывает страницу поиска SpringerLink и возвращает
    общее количество страниц результатов.
    """
    search_url = _build_search_url(query, open_access=only_full_access, date_from=date_from, date_to=date_to)
    _navigate_and_wait(driver, search_url)

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
    date_from: str = "",
    date_to: str = "",
) -> dict:
    """
    Скрапит одну страницу результатов поиска SpringerLink.

    Возвращает словарь:
      - articles: список статей [{title, description, authors}, ...]
      - skipped: количество пропущенных статей (без полного доступа)
    """
    search_url = _build_search_url(query, page=page, open_access=only_full_access, date_from=date_from, date_to=date_to)
    _navigate_and_wait(driver, search_url)

    driver.implicitly_wait(0)

    try:
        cards = driver.find_elements(By.CSS_SELECTOR, "div.app-card-open__main")

        articles = []
        skipped = 0

        for card in cards:
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

            title_els = card.find_elements(
                By.CSS_SELECTOR, 'h3[data-test="title"] span'
            )
            title = title_els[0].text.strip() if title_els else "—"

            link_els = card.find_elements(
                By.CSS_SELECTOR, 'h3[data-test="title"] a'
            )
            url = ""
            if link_els:
                href = link_els[0].get_attribute("href") or ""
                url = href if href.startswith("http") else BASE_URL + href

            desc_els = card.find_elements(
                By.CSS_SELECTOR, '[data-test="description"]'
            )
            description = desc_els[0].text.strip() if desc_els else "—"

            author_els = card.find_elements(
                By.CSS_SELECTOR, '[data-test="authors"]'
            )
            authors = author_els[0].text.strip() if author_els else "—"

            published_els = card.find_elements(
                By.CSS_SELECTOR, '[data-test="published"]'
            )
            published_date = published_els[0].text.strip() if published_els else ""

            articles.append({
                "title": title,
                "url": url,
                "description": description,
                "authors": authors,
                "published_date": published_date,
            })

        return {"articles": articles, "skipped": skipped}
    finally:
        driver.implicitly_wait(WAIT_TIMEOUT)


def scrape_abstract(driver: WebDriver, article_url: str) -> str:
    """
    Переходит на страницу статьи и извлекает текст Abstract.
    """
    scraper = Scraper(driver)
    scraper.go_to(article_url)

    scraper.wait_for('#Abs1-content', timeout=ABSTRACT_LOAD_TIMEOUT)

    driver.implicitly_wait(0)
    try:
        paragraphs = driver.find_elements(By.CSS_SELECTOR, "#Abs1-content p")
        abstract = "\n\n".join(p.text.strip() for p in paragraphs if p.text.strip())
        return abstract or "—"
    finally:
        driver.implicitly_wait(WAIT_TIMEOUT)
