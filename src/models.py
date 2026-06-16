from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ContentItem:
    title: str
    url: str
    source: str
    published_at: str | None = None
    summary: str = ""
    category: str = "general"
    keywords: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScoredItem(ContentItem):
    score: float = 0.0
    score_details: dict[str, float] = field(default_factory=dict)


@dataclass
class BriefingResult:
    mode: str
    date_label: str
    markdown_path: str | None
    html_path: str | None
    item_count: int
    email_sent: bool = False
    llm_used: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
