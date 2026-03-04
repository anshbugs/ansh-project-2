from __future__ import annotations

"""
Phase 1.2 – Raw Page Fetcher

CLI usage (from project root):

    python -m backend.ingestion.fetch_pages

This script:
- Initialises the SQLite database.
- Fetches HTML for all allowed Groww URLs defined in backend.config.
- Upserts entries into the raw_pages table.
"""

import datetime as dt
import logging

import requests

from backend.config import ALLOWED_KB_URLS
from backend.db import get_connection, init_db


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def fetch_url(url: str, timeout: int = 20) -> tuple[int, str]:
    headers = {
        "User-Agent": "Groww-MF-FAQ-Prototype/1.0 (+https://example.com)",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.status_code, resp.text


def upsert_raw_page(url: str, status_code: int, html: str) -> None:
    conn = get_connection()
    try:
        now = dt.datetime.utcnow().isoformat()
        conn.execute(
            """
            INSERT INTO raw_pages (url, html, status_code, fetched_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                html=excluded.html,
                status_code=excluded.status_code,
                fetched_at=excluded.fetched_at;
            """,
            (url, html, status_code, now),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    init_db()
    logging.info("Fetching %d Groww pages", len(ALLOWED_KB_URLS))
    for url in ALLOWED_KB_URLS:
        try:
            logging.info("Fetching %s", url)
            status, html = fetch_url(url)
            upsert_raw_page(url, status, html)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to fetch %s: %s", url, exc)


if __name__ == "__main__":
    main()

