from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

try:
    import requests
except ImportError:  # pragma: no cover - declared dependency, dry-run may not need it.
    requests = None

from src.models import ContentItem
from src.utils.retry import retry


class HTMLListCollector:
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
            self.logger.warning("requests is not installed; skipping HTML list collection.")
            return []

        max_items = int(section_config.get("max_items", 12))
        keywords = section_config.get("keywords", [])
        fallback_enabled = bool(section_config.get("fallback_when_no_keyword_match", False))
        seen_urls: set[str] = set()
        items: list[ContentItem] = []
        fallback_items: list[ContentItem] = []

        for source in section_config.get("sources", []):
            try:
                anchors = retry(lambda s=source: self._fetch_anchors(s), attempts=2)
            except Exception as error:  # noqa: BLE001 - one source must not kill the run.
                self.logger.warning("HTML source failed %s: %s", source.get("url"), error)
                continue

            for title, url in anchors:
                hit_keywords = _matched_keywords(title, keywords)
                item = self._anchor_to_item(source, title, url, hit_keywords)
                if not item or item.url in seen_urls:
                    continue
                if hit_keywords:
                    items.append(item)
                    seen_urls.add(item.url)
                elif fallback_enabled:
                    fallback_items.append(item)
                if len(items) >= max_items:
                    return items

        if fallback_enabled and len(items) < max_items:
            for item in fallback_items:
                if item.url in seen_urls:
                    continue
                items.append(item)
                seen_urls.add(item.url)
                if len(items) >= max_items:
                    break

        return items

    def _fetch_anchors(self, source: dict[str, Any]) -> list[tuple[str, str]]:
        response = self.session.get(
            source["url"],
            headers={
                "User-Agent": (
                    "Mozilla/5.0 personal-briefing-agent/1.0 "
                    "(compatible; policy-monitor)"
                )
            },
            timeout=25,
        )
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        parser = AnchorParser(source["url"], source.get("base_url") or source["url"])
        parser.feed(response.text)
        return parser.anchors

    def _anchor_to_item(
        self,
        source: dict[str, Any],
        title: str,
        url: str,
        hit_keywords: list[str],
    ) -> ContentItem | None:
        title = " ".join(title.split())
        if len(title) < 6 or not url.startswith(("http://", "https://")):
            return None
        return ContentItem(
            title=title,
            url=url,
            source=source.get("name") or source.get("url") or "Policy Source",
            published_at=None,
            summary="中国国家政策官网列表页条目。",
            category=self.category,
            keywords=hit_keywords,
            metadata={"collector": "html_list", "source_url": source.get("url")},
        )


class AnchorParser(HTMLParser):
    def __init__(self, page_url: str, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.base_url = base_url
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        if href:
            self._current_href = urljoin(self.base_url, href)
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or not self._current_href:
            return
        title = " ".join("".join(self._current_text).split())
        if title:
            self.anchors.append((title, self._current_href))
        self._current_href = None
        self._current_text = []


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    return [keyword for keyword in keywords if keyword.lower() in lowered]
