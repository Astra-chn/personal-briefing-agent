from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

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
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
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
            with sqlite3.connect(self.path) as conn:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO items
                    (url, title, source, category, published_at, score, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
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
                        )
                        for item in items
                    ],
                )
        except (sqlite3.Error, OSError) as error:
            self.logger.warning("SQLite save items failed: %s", error)

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
