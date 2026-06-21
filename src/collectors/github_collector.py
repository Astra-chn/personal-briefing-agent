from __future__ import annotations

from datetime import timedelta
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - declared dependency, dry-run may not need it.
    requests = None

from src.models import ContentItem
from src.utils.date_utils import now_beijing
from src.utils.retry import retry


class GitHubCollector:
    API_URL = "https://api.github.com/search/repositories"

    def __init__(
        self,
        config: dict[str, Any],
        logger,
        session: Any | None = None,
    ) -> None:
        self.config = config
        self.logger = logger
        self.session = session or (requests.Session() if requests else None)

    def collect(self) -> list[ContentItem]:
        github_config = self.config.get("github", {})
        if not github_config.get("enabled", True):
            return []

        max_repos = int(github_config.get("max_repos", 10))
        queries = self._build_queries(github_config)
        seen: set[str] = set()
        items: list[ContentItem] = []

        for query_spec in queries:
            try:
                repos = retry(
                    lambda q=query_spec: self._search(q, max_repos),
                    attempts=2,
                    delay_seconds=1,
                )
            except Exception as error:  # noqa: BLE001 - collection must be fault tolerant.
                self.logger.warning("GitHub query failed: %s", error)
                continue

            for repo in repos:
                url = repo.get("html_url", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                items.append(self._repo_to_item(repo))
                if len(items) >= max_repos:
                    return items

        return items

    def _build_queries(self, github_config: dict[str, Any]) -> list[dict[str, str]]:
        min_stars = int(github_config.get("min_stars", 50))
        lookback_days = int(github_config.get("lookback_days", 14))
        fresh_created_days = int(github_config.get("fresh_created_days", 30))
        pushed_after = (now_beijing() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        created_after = (now_beijing() - timedelta(days=fresh_created_days)).strftime("%Y-%m-%d")
        fresh_base = f"stars:>={min_stars} created:>={created_after}"
        updated_base = f"stars:>={min_stars} pushed:>={pushed_after}"

        topics = github_config.get("topics", [])[:6]
        keywords = github_config.get("keywords", [])[:6]
        queries: list[dict[str, str]] = []
        for topic in topics:
            queries.append({"q": f"topic:{topic} {fresh_base}", "sort": "updated"})
        for keyword in keywords:
            queries.append({"q": f"{keyword} in:name,description,readme {fresh_base}", "sort": "updated"})

        # Keep a small high-star fallback, but run it after fresh queries so old
        # evergreen repositories do not dominate every daily briefing.
        for topic in topics[:3]:
            queries.append({"q": f"topic:{topic} {updated_base}", "sort": "stars"})
        return queries or [{"q": fresh_base, "sort": "updated"}]

    def _search(self, query_spec: dict[str, str], max_repos: int) -> list[dict[str, Any]]:
        if self.session is None:
            raise RuntimeError("requests is not installed")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        token = self.config.get("github", {}).get("token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = self.session.get(
            self.API_URL,
            headers=headers,
            params={
                "q": query_spec["q"],
                "sort": query_spec.get("sort", "updated"),
                "order": "desc",
                "per_page": max_repos,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("items", [])

    def _repo_to_item(self, repo: dict[str, Any]) -> ContentItem:
        topics = repo.get("topics") or []
        language = repo.get("language") or "Unknown"
        stars = repo.get("stargazers_count", 0)
        forks = repo.get("forks_count", 0)
        description = repo.get("description") or ""
        title = repo.get("full_name") or repo.get("name") or "Untitled repository"

        summary = f"{description}\nStars: {stars}; Forks: {forks}; Language: {language}"
        return ContentItem(
            title=title,
            url=repo.get("html_url", ""),
            source="GitHub",
            published_at=repo.get("updated_at"),
            summary=summary.strip(),
            category="github",
            keywords=list(topics),
            metadata={
                "stars": stars,
                "forks": forks,
                "language": language,
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
                "topics": topics,
            },
        )
