"""SQLite connection and schema. Phase 0 owns this file; workstreams go through store.py.

One file database, one short-lived connection per call (safe across FastAPI's thread pool).
JSON columns hold Pydantic models serialised with model_dump_json().
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS advisor_sessions (
    id TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    messages_json TEXT NOT NULL DEFAULT '[]',
    stage TEXT NOT NULL DEFAULT 'asking',
    mode TEXT NOT NULL DEFAULT 'rules',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quotes (
    id TEXT PRIMARY KEY,
    profile_json TEXT NOT NULL,
    quote_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL REFERENCES quotes(id),
    pin_hash TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    phone_enc TEXT NOT NULL,
    phone_masked TEXT NOT NULL,
    status TEXT NOT NULL,
    slot_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(id),
    ts TEXT NOT NULL,
    status TEXT NOT NULL,
    text_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_order_events_order ON order_events(order_id);
CREATE TABLE IF NOT EXISTS consents (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    version TEXT NOT NULL,
    purposes_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    withdrawn_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_consents_order ON consents(order_id);
CREATE TABLE IF NOT EXISTS kyc_results (
    order_id TEXT PRIMARY KEY,
    verdict TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    fields_masked_json TEXT NOT NULL DEFAULT '{}',
    gst_products_blocked INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS handoffs (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
"""


def _db_path() -> Path:
    return settings.db_path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path(), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init() -> None:
    _db_path().parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)


def reset() -> None:
    """Drop every table and recreate the schema (tests and the demo reset only)."""
    with connect() as conn:
        for table in ("order_events", "orders", "quotes", "consents", "kyc_results", "handoffs", "advisor_sessions"):
            conn.execute(f"DROP TABLE IF EXISTS {table}")
    init()
