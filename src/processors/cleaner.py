from __future__ import annotations

import html
import re
from datetime import datetime

from src.models import ContentItem


TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_items(items: list[ContentItem], summary_limit: int = 600) -> list[ContentItem]:
    cleaned: list[ContentItem] = []
    for item in items:
        normalized = clean_item(item, summary_limit=summary_limit)
        if normalized:
            cleaned.append(normalized)
    return cleaned


def clean_item(item: ContentItem, summary_limit: int = 600) -> ContentItem | None:
    title = normalize_text(item.title)
    url = normalize_text(item.url)
    if not title or not url:
        return None

    summary = normalize_text(item.summary)
    if len(summary) > summary_limit:
        summary = f"{summary[:summary_limit].rstrip()}..."

    item.title = title
    item.url = url
    item.source = normalize_text(item.source) or "Unknown"
    item.summary = summary
    item.published_at = normalize_datetime(item.published_at)
    item.keywords = sorted({normalize_text(keyword) for keyword in item.keywords if normalize_text(keyword)})
    item.references = sorted({ref for ref in item.references if ref and ref != item.url})
    return item


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = TAG_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def normalize_datetime(value: str | None) -> str | None:
    if not value:
        return None
    text = normalize_text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return text
