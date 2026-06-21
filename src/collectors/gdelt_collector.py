from __future__ import annotations

from datetime import datetime
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - declared dependency, dry-run may not need it.
    requests = None

from src.models import ContentItem
from src.utils.retry import retry


class GDELTCollector:
    API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

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
        if self.session is None:
            self.logger.warning("requests is not installed; skipping GDELT collection.")
            return []

        max_items = int(section_config.get("max_items", 15))
        queries = section_config.get("gdelt_queries", [])
        seen_urls: set[str] = set()
        items: list[ContentItem] = []

        for query in queries:
            try:
                articles = retry(lambda q=query: self._search(q, max_items), attempts=2)
            except Exception as error:  # noqa: BLE001 - one query must not kill the run.
                self.logger.warning("GDELT query failed %s: %s", query, error)
                continue

            for article in articles:
                item = self._article_to_item(article, query)
                if not item or item.url in seen_urls:
                    continue
                items.append(item)
                seen_urls.add(item.url)
                if len(items) >= max_items:
                    return items

        return items

    def _search(self, query: str, max_items: int) -> list[dict[str, Any]]:
        response = self.session.get(
            self.API_URL,
            params={
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": max_items,
                "sort": "HybridRel",
                "timespan": "3d",
            },
            headers={"User-Agent": "personal-briefing-agent/1.0"},
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("articles", [])

    def _article_to_item(self, article: dict[str, Any], query: str) -> ContentItem | None:
        title = (article.get("title") or "").strip()
        url = (article.get("url") or "").strip()
        if not title or not url:
            return None

        source = (
            article.get("sourceCommonName")
            or article.get("domain")
            or article.get("sourceCountry")
            or "GDELT"
        )
        summary = article.get("seendate") or "GDELT international news result"
        published_at = _normalize_gdelt_date(article.get("seendate"))
        return ContentItem(
            title=title,
            url=url,
            source=str(source),
            published_at=published_at,
            summary=str(summary),
            category=self.category,
            keywords=[query],
            metadata={
                "collector": "gdelt",
                "domain": article.get("domain"),
                "language": article.get("language"),
                "source_country": article.get("sourceCountry"),
            },
        )


def _normalize_gdelt_date(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            continue
    return value
