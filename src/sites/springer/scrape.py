import os
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from config import DOWNLOAD_DIR
from scraper import Scraper
from sites.springer.config import (
    BASE_URL,
    ONLY_FULL_ACCESS,
    OUTPUT_FILE,
    SEARCH_QUERY,
)


def run(driver: WebDriver):
    scraper = Scraper(driver)

    # --- Формирование URL поиска и открытие страницы ---
    # Подставляем поисковый запрос из config в URL SpringerLink
    search_url = f"{BASE_URL}/search?query={quote_plus(SEARCH_QUERY)}"
    print(f"[springer] Opening: {search_url}")
    scraper.go_to(search_url)

    # --- Ожидание загрузки результатов ---
    # Ждём появления хотя бы одного заголовка статьи на странице
    scraper.wait_for('[data-test="title"]', timeout=20)
    print(f"[springer] Page loaded: {driver.title}")

    # --- Поиск всех карточек статей на странице ---
    # Каждая карточка — это div.app-card-open__main, содержит заголовок,
    # описание, авторов и мета-информацию о доступе
    cards = driver.find_elements(By.CSS_SELECTOR, "div.app-card-open__main")
    print(f"[springer] Found {len(cards)} article(s) on the page")

    if ONLY_FULL_ACCESS:
        print("[springer] Filter: only Full access articles")
    else:
        print("[springer] Filter: all articles (including restricted)")
    print()

    # --- Цикл по карточкам: проверка доступа и извлечение данных ---
    articles = []
    skipped = 0

    for card in cards:
        # --- Проверка доступа к статье ---
        # У статей с полным доступом внутри карточки есть элемент
        # [data-test="entitlements"] с текстом "Full access".
        # У статей без полного доступа этого элемента нет.
        # Если ONLY_FULL_ACCESS=True, пропускаем статьи без полного доступа.
        # Чтобы включить все статьи, поменяйте ONLY_FULL_ACCESS на False в config.py.
        entitlement_els = card.find_elements(By.CSS_SELECTOR, '[data-test="entitlements"]')
        has_full_access = (
            entitlement_els
            and "full access" in entitlement_els[0].text.strip().lower()
        )
        if ONLY_FULL_ACCESS and not has_full_access:
            skipped += 1
            continue

        # --- Извлечение заголовка статьи ---
        # Заголовок находится в <h3 data-test="title"> -> <span>
        title_els = card.find_elements(By.CSS_SELECTOR, 'h3[data-test="title"] span')
        title = title_els[0].text.strip() if title_els else "—"

        # --- Извлечение описания статьи ---
        # Описание находится в <div data-test="description"> -> <p>
        # Может отсутствовать у некоторых статей
        desc_els = card.find_elements(By.CSS_SELECTOR, '[data-test="description"] p')
        description = desc_els[0].text.strip() if desc_els else "—"

        # --- Извлечение авторов статьи ---
        # Авторы находятся в <span data-test="authors">
        author_els = card.find_elements(By.CSS_SELECTOR, '[data-test="authors"]')
        authors = author_els[0].text.strip() if author_els else "—"

        # --- Добавление статьи в список результатов ---
        num = len(articles) + 1
        articles.append({
            "number": num,
            "title": title,
            "description": description,
            "authors": authors,
        })

        print(f"{num}. {title}")
        print(f"   Описание: {description[:120]}...")
        print(f"   Авторы: {authors}")
        print()

    if skipped:
        print(f"[springer] Skipped {skipped} article(s) without full access\n")

    # --- Запись результатов в файл ---
    # Создаём папку downloads, если её нет, и записываем результаты
    # в текстовый файл в читаемом формате
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Запрос: {SEARCH_QUERY}\n")
        f.write(f"Фильтр: {'только Full access' if ONLY_FULL_ACCESS else 'все статьи'}\n")
        f.write(f"Найдено статей: {len(articles)}\n")
        f.write("=" * 80 + "\n\n")

        for a in articles:
            f.write(f"{a['number']}. {a['title']}\n")
            f.write(f"   Описание: {a['description']}\n")
            f.write(f"   Авторы: {a['authors']}\n")
            f.write("-" * 80 + "\n\n")

    print(f"[springer] Results saved to {OUTPUT_FILE}")
