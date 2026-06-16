from __future__ import annotations

from email.utils import parsedate_to_datetime
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - declared dependency, dry-run may not need it.
    requests = None

try:
    import feedparser
except ImportError:  # pragma: no cover - declared dependency, defensive for dry environments.
    feedparser = None

from src.models import ContentItem
from src.utils.retry import retry


class RSSCollector:
    def __init__(
        self,
        config: dict[str, Any],
        section_name: str,
        category: str,
        logger,
        session: Any | None = None,
    ) -> None:
        self.config = config
        self.section_name = section_name
        self.category = category
        self.logger = logger
        self.session = session or (requests.Session() if requests else None)

    def collect(self) -> list[ContentItem]:
        section_config = self.config.get(self.section_name, {})
        if not section_config.get("enabled", True):
            return []

        max_items = int(section_config.get("max_items", 15))
        fallback_enabled = bool(section_config.get("fallback_when_no_keyword_match", False))
        fallback_min_items = int(section_config.get("fallback_min_items", 0))
        keywords = section_config.get("keywords", [])
        sources = section_config.get("rss_sources", [])
        items: list[ContentItem] = []
        fallback_items: list[ContentItem] = []

        for url in sources:
            try:
                entries = retry(lambda source=url: self._fetch_feed(source), attempts=2)
            except Exception as error:  # noqa: BLE001 - one bad feed must not kill the run.
                self.logger.warning("RSS source failed %s: %s", url, error)
                continue

            for entry in entries:
                item = self._entry_to_item(entry, url, keywords)
                if not item:
                    if fallback_enabled:
                        fallback_item = self._entry_to_item(entry, url, keywords, require_keyword=False)
                        if fallback_item:
                            fallback_items.append(fallback_item)
                    continue
                items.append(item)
                if len(items) >= max_items:
                    return items

        if fallback_enabled and len(items) < fallback_min_items:
            seen_urls = {item.url for item in items}
            for item in fallback_items:
                if item.url in seen_urls:
                    continue
                items.append(item)
                seen_urls.add(item.url)
                if len(items) >= min(max_items, fallback_min_items):
                    break

        return items

    def _fetch_feed(self, url: str) -> list[Any]:
        if self.session is None:
            self.logger.warning("requests is not installed; skipping RSS source %s", url)
            return []
        if feedparser is None:
            self.logger.warning("feedparser is not installed; skipping RSS source %s", url)
            return []

        response = self.session.get(url, timeout=20, headers={"User-Agent": "personal-briefing-agent/1.0"})
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", []):
            raise ValueError(f"invalid RSS feed: {url}")
        return list(getattr(parsed, "entries", []))

    def _entry_to_item(
        self,
        entry: Any,
        source_url: str,
        keywords: list[str],
        require_keyword: bool = True,
    ) -> ContentItem | None:
        title = _entry_get(entry, "title", "").strip()
        link = _entry_get(entry, "link", "").strip()
        if not title or not link:
            return None

        summary = (
            _entry_get(entry, "summary", "")
            or _entry_get(entry, "description", "")
            or _entry_get(entry, "subtitle", "")
        )
        published_at = _normalize_datetime(
            _entry_get(entry, "published", "")
            or _entry_get(entry, "updated", "")
        )
        source = _entry_get(entry, "source", {}) or {}
        source_title = source.get("title") if isinstance(source, dict) else ""
        hit_keywords = _matched_keywords(f"{title} {summary}", keywords)

        if require_keyword and keywords and not hit_keywords:
            return None

        return ContentItem(
            title=title,
            url=link,
            source=source_title or _source_name_from_url(source_url),
            published_at=published_at,
            summary=summary,
            category=self.category,
            keywords=hit_keywords,
            metadata={"feed_url": source_url},
        )


def _entry_get(entry: Any, key: str, default: Any = None) -> Any:
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]


def _normalize_datetime(value: str) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError):
        return value


def _source_name_from_url(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").split("/", 1)[0]
