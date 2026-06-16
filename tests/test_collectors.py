from types import SimpleNamespace

from src.collectors.github_collector import GitHubCollector
from src.collectors import rss_collector
from src.collectors.rss_collector import RSSCollector


class FakeResponse:
    def __init__(self, payload=None, content=b"feed"):
        self.payload = payload or {}
        self.content = content

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_github_collector_maps_repositories():
    payload = {
        "items": [
            {
                "full_name": "example/agent",
                "html_url": "https://github.com/example/agent",
                "description": "AI Agent demo",
                "stargazers_count": 1200,
                "forks_count": 20,
                "language": "Python",
                "topics": ["ai", "agent"],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
            }
        ]
    }
    config = {"github": {"enabled": True, "max_repos": 1, "min_stars": 10, "topics": ["ai"], "keywords": []}}
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    items = GitHubCollector(config, logger, session=FakeSession(FakeResponse(payload))).collect()

    assert len(items) == 1
    assert items[0].title == "example/agent"
    assert items[0].metadata["stars"] == 1200


def test_rss_collector_skips_non_matching_and_maps_matching(monkeypatch):
    entries = [
        {"title": "Sports item", "link": "https://example.com/sports", "summary": "football"},
        {
            "title": "DeepSeek Agent update",
            "link": "https://example.com/ai",
            "summary": "AI Agent news",
            "published": "Tue, 16 Jun 2026 00:00:00 GMT",
        },
    ]
    monkeypatch.setattr(rss_collector, "feedparser", SimpleNamespace(parse=lambda content: SimpleNamespace(entries=entries, bozo=False)))
    config = {
        "ai_news": {
            "enabled": True,
            "max_items": 5,
            "keywords": ["DeepSeek", "AI Agent"],
            "rss_sources": ["https://feeds.example.com/ai.xml"],
        }
    }
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    items = RSSCollector(config, "ai_news", "ai_news", logger, session=FakeSession(FakeResponse())).collect()

    assert len(items) == 1
    assert items[0].title == "DeepSeek Agent update"
    assert "DeepSeek" in items[0].keywords
