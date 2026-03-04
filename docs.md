# Scrapper — документация проекта

## Назначение

Веб-скраппер для поиска и извлечения научных статей с сайта SpringerLink.
Пользователь вводит ключевые слова, выбирает диапазон страниц и параметры фильтрации,
после чего система автоматически собирает информацию о статьях (название, описание, авторы).

Проект состоит из двух частей:
- **Backend** — API-сервер на FastAPI, управляющий браузером через Selenium
- **Frontend** — веб-интерфейс на Next.js для взаимодействия с пользователем

---

## Архитектура

Проект состоит из 3 Docker-сервисов:

```
┌─────────────────┐     /api/* rewrite     ┌──────────────────┐     WebDriver :4444     ┌─────────────────┐
│  frontend :3000 │ ──────────────────────► │  backend :8000   │ ──────────────────────► │  chrome (Selenium)│
│  (Next.js)      │                        │  (FastAPI)       │                        │  standalone      │
└─────────────────┘                        └──────────────────┘                        └─────────────────┘
```

- **chrome** — контейнер `selenium/standalone-chrome`, предоставляет удалённый браузер
- **backend** — Python-приложение (FastAPI + uvicorn), подключается к Chrome через Selenium WebDriver
- **frontend** — Next.js dev server, проксирует `/api/*` запросы на backend

---

## Стек технологий

| Компонент | Технологии |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, uvicorn, Selenium, BeautifulSoup4, uv (менеджер пакетов) |
| Frontend | Next.js (App Router), React, TypeScript, TanStack Query |
| Браузер | Selenium Standalone Chrome (Docker) |
| Оркестрация | Docker Compose |

---

## Структура проекта

```
scrapper/
├── backend/
│   ├── src/
│   │   ├── app.py               # FastAPI-приложение с эндпоинтами
│   │   ├── config.py            # общие настройки (CHROME_URL, DOWNLOAD_DIR и т.д.)
│   │   ├── browser.py           # создание экземпляра Chrome через Selenium Remote
│   │   ├── scraper.py           # базовый класс Scraper с утилитами навигации
│   │   ├── downloader.py        # скачивание файлов с передачей cookies
│   │   └── sites/
│   │       └── springer/
│   │           └── scrape.py    # логика скраппинга SpringerLink
│   ├── pyproject.toml           # зависимости Python (управление через uv)
│   ├── uv.lock                  # зафиксированные версии зависимостей
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/
│   ├── src/
│   │   └── app/
│   │       ├── layout.tsx       # корневой layout с QueryClientProvider
│   │       ├── providers.tsx    # клиентский компонент для TanStack Query
│   │       ├── page.tsx         # главная страница (управление состоянием)
│   │       ├── globals.css      # глобальные стили
│   │       └── components/
│   │           ├── SearchForm.tsx    # форма поиска с настройками
│   │           └── ResultsTable.tsx  # таблица результатов
│   ├── next.config.ts           # rewrites для проксирования /api -> backend
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .dockerignore
├── docker-compose.yml           # оркестрация 3 сервисов
├── downloads/                   # результаты скраппинга (volume)
└── docs.md                      # этот файл
```

---

## API-эндпоинты

### `GET /api/springer/page-count`

Получить количество страниц результатов поиска.

**Параметры запроса:**
| Параметр | Тип | Обязательный | Описание |
|----------|------|-------------|----------|
| `query` | string | да | Поисковый запрос (минимум 1 символ) |

**Ответ:**
```json
{
  "total_pages": 67
}
```

### `POST /api/springer/scrape`

Скрапить статьи с указанных страниц.

**Тело запроса (JSON):**
```json
{
  "query": "surface alloying of iron castings",
  "page_from": 1,
  "page_to": 3,
  "only_full_access": true
}
```

| Поле | Тип | По умолчанию | Описание |
|------|------|-------------|----------|
| `query` | string | — | Поисковый запрос |
| `page_from` | int | 1 | Начальная страница |
| `page_to` | int | 1 | Конечная страница |
| `only_full_access` | bool | true | Только статьи с полным доступом |

**Ответ:**
```json
{
  "articles": [
    {
      "title": "Название статьи",
      "description": "Описание статьи...",
      "authors": "Автор 1, Автор 2"
    }
  ],
  "total": 12,
  "skipped": 5
}
```

---

## Как запустить

### Требования
- Docker и Docker Compose

### Запуск

```bash
docker compose up --build
```

Откройте в браузере: **http://localhost:3000**

### Использование

1. Введите ключевые слова в поле поиска
2. Дождитесь автоматического определения количества страниц
3. Выберите диапазон страниц для скраппинга
4. Включите/выключите фильтр "Только Full access"
5. Нажмите "Запустить скраппинг"
6. Результаты появятся в таблице ниже

---

## Как добавить новый сайт

1. Создайте папку `backend/src/sites/newsite/`
2. Создайте файл `__init__.py` (пустой)
3. Создайте файл `scrape.py` с функциями:
   - `get_page_count(driver, query) -> int` — возвращает кол-во страниц
   - `scrape_page(driver, query, page, only_full_access) -> dict` — скрапит одну страницу
4. Добавьте новые эндпоинты в `backend/src/app.py`:
   ```python
   from sites.newsite.scrape import get_page_count as newsite_page_count
   from sites.newsite.scrape import scrape_page as newsite_scrape_page

   @app.get("/api/newsite/page-count")
   async def newsite_page_count_endpoint(query: str = Query(...)):
       # аналогично springer
       ...
   ```

---

## Конфигурация

### Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|-----------|----------------------|----------|
| `CHROME_URL` | `http://localhost:4444/wd/hub` | URL удалённого WebDriver (Chrome) |

В Docker Compose `CHROME_URL` автоматически устанавливается в `http://chrome:4444/wd/hub`.

### Настройки в `backend/src/config.py`

| Параметр | Значение | Описание |
|----------|---------|----------|
| `DOWNLOAD_DIR` | `../downloads` (относительно src/) | Папка для скачанных файлов |
| `WAIT_TIMEOUT` | `15` | Таймаут ожидания элементов (секунды) |
| `HEADLESS` | `True` | Запуск Chrome в headless-режиме |
