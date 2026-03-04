from __future__ import annotations

"""
Lightweight SQLite storage for the prototype.

This implements the tables required in Phase 1 and Phase 2:
- raw_pages: stores fetched HTML for each allowed Groww URL.
- mutual_fund_schemes: structured scheme-level attributes (may be partially filled).
- kb_chunks: unstructured text chunks with metadata.
- kb_chunk_embeddings: embeddings for each chunk (Phase 2).
"""

import sqlite3
from pathlib import Path
from typing import Iterable, Tuple


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "kb.sqlite"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialise all required tables if they don't already exist."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Raw HTML storage.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                html TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                fetched_at TEXT NOT NULL
            );
            """
        )

        # Structured scheme attributes (may be sparsely populated initially).
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mutual_fund_schemes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_name TEXT,
                scheme_slug TEXT UNIQUE,
                amc_name TEXT,
                expense_ratio TEXT,
                exit_load TEXT,
                min_sip_amount TEXT,
                min_lumpsum_amount TEXT,
                risk_level TEXT,
                benchmark_index TEXT,
                category TEXT,
                plan_type TEXT,
                underlying_url TEXT,
                as_of_date TEXT,
                last_parsed_at TEXT
            );
            """
        )

        # Unstructured chunks extracted from pages.
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE,
                url TEXT NOT NULL,
                page_type TEXT NOT NULL,
                scheme_slug TEXT,
                section_title TEXT,
                content TEXT NOT NULL,
                token_count INTEGER,
                last_parsed_at TEXT
            );
            """
        )

        # Embeddings for each chunk (stored as JSON text for the prototype).
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_chunk_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT UNIQUE NOT NULL,
                embedding_json TEXT NOT NULL
            );
            """
        )

        conn.commit()
    finally:
        conn.close()


def executemany(conn: sqlite3.Connection, sql: str, rows: Iterable[Tuple]) -> None:
    cur = conn.cursor()
    cur.executemany(sql, rows)
    conn.commit()


__all__ = ["get_connection", "init_db", "DB_PATH", "DATA_DIR"]

