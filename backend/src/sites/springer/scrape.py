import logging
import math
import re
import time
from urllib.parse import quote_plus

from bs4 import BeautifulSoup, NavigableString, Tag
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
        if "Client Challenge" in driver.title:
            return True
        driver.implicitly_wait(0)
        return bool(
            driver.find_elements(By.CSS_SELECTOR, "div.challenge-container, #challenge-running")
        )
    except Exception:
        return False
    finally:
        driver.implicitly_wait(WAIT_TIMEOUT)


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


ARTICLES_PER_PAGE = 20


def _build_search_url(
    query: str,
    page: int = 1,
    date_from: str = "",
    date_to: str = "",
) -> str:
    url = f"{BASE_URL}/search?query={quote_plus(query)}&sortBy=relevance&page={page}"
    if date_from or date_to:
        url += f"&date=custom&dateFrom={date_from}&dateTo={date_to}"
    return url


def _get_pagination_max(driver: WebDriver) -> int:
    """Extract max page number from Springer pagination."""
    driver.implicitly_wait(0)
    try:
        page_items = driver.find_elements(
            By.CSS_SELECTOR, "li.eds-c-pagination__item[data-page]"
        )
    finally:
        driver.implicitly_wait(WAIT_TIMEOUT)

    if not page_items:
        return 1
    return max(int(item.get_attribute("data-page")) for item in page_items)


def _get_open_access_count(driver: WebDriver) -> int | None:
    """
    Extract the Open Access article count from the filter panel HTML.
    Springer renders the filter label as:
      <label for="publishing-model-open access">
        <span>Open access</span><span>(74)</span>
      </label>
    """
    try:
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        label = soup.find("label", attrs={"for": "publishing-model-open access"})
        if label:
            label_text = label.get_text(strip=True)
            m = re.search(r"\((\d[\d,]*)\)", label_text)
            if m:
                count = int(m.group(1).replace(",", ""))
                logger.info("Open access count from label: %d", count)
                return count

        cb = soup.find("input", attrs={"id": "publishing-model-open access"})
        if cb:
            parent = cb.parent
            if parent:
                parent_text = parent.get_text(strip=True)
                m = re.search(r"\((\d[\d,]*)\)", parent_text)
                if m:
                    count = int(m.group(1).replace(",", ""))
                    logger.info("Open access count from parent: %d", count)
                    return count

        logger.warning("Could not find open access count in filter HTML")

    except Exception as e:
        logger.warning("Failed to extract open access count: %s", e)

    return None


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

    При only_full_access=True извлекает число Open Access статей
    из панели фильтров и вычисляет количество страниц.
    """
    search_url = _build_search_url(query, date_from=date_from, date_to=date_to)
    _navigate_and_wait(driver, search_url)

    if only_full_access:
        oa_count = _get_open_access_count(driver)
        if oa_count is not None:
            return max(1, math.ceil(oa_count / ARTICLES_PER_PAGE))
        logger.warning("Could not get open access count, falling back to total pagination")

    return _get_pagination_max(driver)


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
    search_url = _build_search_url(query, page=page, date_from=date_from, date_to=date_to)
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


def _clean_paragraph_text(tag: Tag) -> str:
    """Extract readable text from a <p>, stripping inline reference markers like [1,2,3]."""
    for sup in tag.find_all("sup"):
        if sup.find("a", attrs={"data-test": "citation-ref"}):
            sup.decompose()
    text = tag.get_text(separator="", strip=False)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def scrape_full_article(driver: WebDriver, article_url: str) -> dict:
    """
    Переходит на страницу статьи и извлекает:
      - abstract
      - sections (с подзаголовками)
      - references (список литературы)
    """
    scraper = Scraper(driver)
    scraper.go_to(article_url)
    _dismiss_cookie_consent(driver)

    scraper.wait_for("div.main-content, #Abs1-content", timeout=ABSTRACT_LOAD_TIMEOUT)
    time.sleep(1)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    abstract = _parse_abstract(soup)
    sections = _parse_sections(soup)
    references = _parse_references(soup)

    return {
        "abstract": abstract,
        "sections": sections,
        "references": references,
    }


def _parse_abstract(soup: BeautifulSoup) -> str:
    abs_div = soup.select_one("#Abs1-content")
    if not abs_div:
        return "—"
    paragraphs = abs_div.find_all("p")
    texts = []
    for p in paragraphs:
        t = _clean_paragraph_text(p)
        if t:
            texts.append(t)
    return "\n\n".join(texts) or "—"


def _parse_sections(soup: BeautifulSoup) -> list[dict]:
    sections: list[dict] = []
    order = 0

    main = soup.select_one("div.main-content")
    if not main:
        return sections

    for section_tag in main.find_all("section", attrs={"data-title": True}):
        data_title = section_tag["data-title"]
        if data_title.lower() == "abstract":
            continue

        content_div = section_tag.select_one(".c-article-section__content")
        if not content_div:
            continue

        current_title = data_title
        current_level = 2
        current_paragraphs: list[str] = []

        def _flush():
            nonlocal order
            if current_paragraphs:
                sections.append({
                    "title": current_title,
                    "content": "\n\n".join(current_paragraphs),
                    "heading_level": current_level,
                    "order_index": order,
                })
                order += 1

        for child in content_div.children:
            if not isinstance(child, Tag):
                continue

            is_subheading = (
                child.name == "h3"
                or (child.has_attr("class") and "c-article__sub-heading" in child.get("class", []))
            )

            if is_subheading:
                _flush()
                current_title = child.get_text(strip=True)
                current_level = 3
                current_paragraphs = []
                continue

            if child.name == "p":
                text = _clean_paragraph_text(child)
                if text:
                    current_paragraphs.append(text)

        _flush()

    return sections


def _parse_references(soup: BeautifulSoup) -> list[dict]:
    references: list[dict] = []
    ref_list = soup.select("ol.c-article-references > li")

    for li in ref_list:
        counter = li.get("data-counter", "").strip().rstrip(".")
        try:
            ref_number = int(counter)
        except (ValueError, TypeError):
            ref_number = len(references) + 1

        text_el = li.select_one(".c-article-references__text")
        text = text_el.get_text(strip=True) if text_el else li.get_text(strip=True)

        doi = ""
        doi_link = li.select_one("a[data-doi]")
        if doi_link:
            doi = doi_link.get("data-doi", "")

        references.append({
            "ref_number": ref_number,
            "text": text,
            "doi": doi,
        })

    return references
