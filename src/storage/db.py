from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from datetime import UTC, datetime

from src.models import BriefingResult, ScoredItem


class BriefingDB:
    def __init__(self, path: str | Path, logger) -> None:
        self.path = Path(path)
        self.logger = logger

    def initialize(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS items (
                        url TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        source TEXT,
                        category TEXT,
                        published_at TEXT,
                        score REAL,
                        payload TEXT,
                        first_seen_at TEXT,
                        last_seen_at TEXT,
                        seen_count INTEGER DEFAULT 1,
                        last_selected_at TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                self._ensure_item_history_columns(conn)
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        mode TEXT NOT NULL,
                        date_label TEXT NOT NULL,
                        item_count INTEGER NOT NULL,
                        markdown_path TEXT,
                        html_path TEXT,
                        email_sent INTEGER,
                        llm_used INTEGER,
                        created_at TEXT
                    )
                    """
                )
        except sqlite3.Error as error:
            self.logger.warning("SQLite initialize failed: %s", error)

    def save_items(self, items: list[ScoredItem]) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            now = datetime.now(UTC).isoformat()
            with sqlite3.connect(self.path) as conn:
                self._ensure_item_history_columns(conn)
                conn.executemany(
                    """
                    INSERT INTO items
                    (url, title, source, category, published_at, score, payload,
                     first_seen_at, last_seen_at, seen_count, last_selected_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title = excluded.title,
                        source = excluded.source,
                        category = excluded.category,
                        published_at = excluded.published_at,
                        score = excluded.score,
                        payload = excluded.payload,
                        last_seen_at = excluded.last_seen_at,
                        seen_count = COALESCE(items.seen_count, 0) + 1,
                        last_selected_at = excluded.last_selected_at
                    """,
                    [
                        (
                            item.url,
                            item.title,
                            item.source,
                            item.category,
                            item.published_at,
                            item.score,
                            json.dumps(item.to_dict(), ensure_ascii=False),
                            now,
                            now,
                            now,
                        )
                        for item in items
                    ],
                )
        except (sqlite3.Error, OSError) as error:
            self.logger.warning("SQLite save items failed: %s", error)

    def get_item_history(self, urls: list[str] | None = None) -> dict[str, dict[str, Any]]:
        try:
            if not self.path.exists():
                return {}
            with sqlite3.connect(self.path) as conn:
                conn.row_factory = sqlite3.Row
                self._ensure_item_history_columns(conn)
                if urls:
                    placeholders = ",".join("?" for _ in urls)
                    rows = conn.execute(
                        f"""
                        SELECT url, category, score, first_seen_at, last_seen_at,
                               seen_count, last_selected_at
                        FROM items
                        WHERE url IN ({placeholders})
                        """,
                        urls,
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT url, category, score, first_seen_at, last_seen_at,
                               seen_count, last_selected_at
                        FROM items
                        """
                    ).fetchall()
                return {row["url"]: dict(row) for row in rows}
        except (sqlite3.Error, OSError) as error:
            self.logger.warning("SQLite history read failed: %s", error)
            return {}

    def save_run(self, result: BriefingResult) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path) as conn:
                conn.execute(
                    """
                    INSERT INTO runs
                    (mode, date_label, item_count, markdown_path, html_path, email_sent, llm_used, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.mode,
                        result.date_label,
                        result.item_count,
                        result.markdown_path,
                        result.html_path,
                        int(result.email_sent),
                        int(result.llm_used),
                        result.created_at,
                    ),
                )
        except (sqlite3.Error, OSError) as error:
            self.logger.warning("SQLite save run failed: %s", error)

    def _ensure_item_history_columns(self, conn: sqlite3.Connection) -> None:
        existing = {
            row[1]
            for row in conn.execute("PRAGMA table_info(items)").fetchall()
        }
        columns = {
            "first_seen_at": "TEXT",
            "last_seen_at": "TEXT",
            "seen_count": "INTEGER DEFAULT 1",
            "last_selected_at": "TEXT",
        }
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE items ADD COLUMN {column} {definition}")
