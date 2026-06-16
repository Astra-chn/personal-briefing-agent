from __future__ import annotations

from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.models import ContentItem


TRACKING_PREFIXES = ("utm_",)
TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid"}


def deduplicate_items(items: list[ContentItem], title_threshold: float = 0.9) -> list[ContentItem]:
    by_url: dict[str, ContentItem] = {}
    result: list[ContentItem] = []

    for item in items:
        canonical_url = canonicalize_url(item.url)
        item.url = canonical_url
        if canonical_url in by_url:
            _merge_item(by_url[canonical_url], item)
            continue

        duplicate = _find_title_duplicate(result, item, title_threshold)
        if duplicate:
            _merge_item(duplicate, item)
            continue

        by_url[canonical_url] = item
        result.append(item)

    return result


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query_pairs = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in TRACKING_KEYS and not key.startswith(TRACKING_PREFIXES)
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/") or "/",
            urlencode(query_pairs),
            "",
        )
    )


def _find_title_duplicate(
    existing_items: list[ContentItem],
    item: ContentItem,
    threshold: float,
) -> ContentItem | None:
    normalized_title = _normalize_title(item.title)
    for existing in existing_items:
        if existing.category != item.category:
            continue
        ratio = SequenceMatcher(None, _normalize_title(existing.title), normalized_title).ratio()
        if ratio >= threshold:
            return existing
    return None


def _merge_item(primary: ContentItem, duplicate: ContentItem) -> None:
    if duplicate.url != primary.url and duplicate.url not in primary.references:
        primary.references.append(duplicate.url)
    primary.keywords = sorted(set(primary.keywords) | set(duplicate.keywords))
    if len(duplicate.summary) > len(primary.summary):
        primary.summary = duplicate.summary


def _normalize_title(title: str) -> str:
    return " ".join(title.lower().split())
