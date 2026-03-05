import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "scrapper.db")


def _get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scrape_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_date TEXT NOT NULL DEFAULT '',
                authors TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                abstract TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES scrape_sessions(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
    finally:
        conn.close()


def create_session(query: str) -> int:
    conn = _get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO scrape_sessions (query, created_at) VALUES (?, ?)",
            (query, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def insert_articles(session_id: int, articles: list[dict]) -> list[int]:
    conn = _get_connection()
    try:
        ids = []
        now = datetime.utcnow().isoformat()
        for art in articles:
            cur = conn.execute(
                """INSERT INTO articles
                   (session_id, title, url, published_date, authors, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_id,
                    art.get("title", ""),
                    art.get("url", ""),
                    art.get("published_date", ""),
                    art.get("authors", ""),
                    art.get("description", ""),
                    now,
                ),
            )
            ids.append(cur.lastrowid)
        conn.commit()
        return ids
    finally:
        conn.close()


def get_session(session_id: int) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM scrape_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_articles_by_session(session_id: int) -> list[dict]:
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM articles WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_article(article_id: int) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_article_abstract(article_id: int, abstract: str):
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE articles SET abstract = ? WHERE id = ?",
            (abstract, article_id),
        )
        conn.commit()
    finally:
        conn.close()
