from types import SimpleNamespace

from src.collectors.gdelt_collector import GDELTCollector
from src.collectors.github_collector import GitHubCollector
from src.collectors.html_list_collector import HTMLListCollector
from src.collectors import rss_collector
from src.collectors.rss_collector import RSSCollector


class FakeResponse:
    def __init__(self, payload=None, content=b"feed", text=""):
        self.payload = payload or {}
        self.content = content
        self.text = text
        self.encoding = "utf-8"

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


def test_rss_collector_can_fallback_when_no_keywords_match(monkeypatch):
    entries = [
        {"title": "World leaders meet for summit", "link": "https://example.com/world", "summary": "Diplomacy update"},
        {"title": "Markets react to election", "link": "https://example.com/market", "summary": "Global market update"},
    ]
    monkeypatch.setattr(rss_collector, "feedparser", SimpleNamespace(parse=lambda content: SimpleNamespace(entries=entries, bozo=False)))
    config = {
        "world_news": {
            "enabled": True,
            "max_items": 5,
            "fallback_when_no_keyword_match": True,
            "fallback_min_items": 2,
            "keywords": ["semiconductor"],
            "rss_sources": ["https://feeds.example.com/world.xml"],
        }
    }
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    items = RSSCollector(config, "world_news", "world_news", logger, session=FakeSession(FakeResponse())).collect()

    assert len(items) == 2
    assert items[0].category == "world_news"


def test_gdelt_collector_maps_articles():
    payload = {
        "articles": [
            {
                "title": "US and China discuss semiconductor export controls",
                "url": "https://example.com/world-policy",
                "sourceCommonName": "Example News",
                "seendate": "20260621T020000Z",
                "domain": "example.com",
                "language": "English",
                "sourceCountry": "US",
            }
        ]
    }
    config = {
        "world_news": {
            "enabled": True,
            "max_items": 5,
            "gdelt_queries": ["semiconductor export controls"],
        }
    }
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    items = GDELTCollector(config, "world_news", "world_news", logger, session=FakeSession(FakeResponse(payload))).collect()

    assert len(items) == 1
    assert items[0].category == "world_news"
    assert items[0].source == "Example News"


def test_html_list_collector_maps_policy_links():
    html = """
    <html><body>
      <a href="/policy/ai.html">关于促进人工智能和数字经济发展的政策</a>
      <a href="/sports.html">体育新闻</a>
    </body></html>
    """
    config = {
        "china_policy": {
            "enabled": True,
            "max_items": 5,
            "keywords": ["人工智能", "数字经济"],
            "sources": [
                {
                    "name": "中国政府网",
                    "url": "https://www.gov.cn/zhengce/zuixin/",
                    "base_url": "https://www.gov.cn",
                }
            ],
        }
    }
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    items = HTMLListCollector(config, "china_policy", "china_policy", logger, session=FakeSession(FakeResponse(text=html))).collect()

    assert len(items) == 1
    assert items[0].category == "china_policy"
    assert items[0].url == "https://www.gov.cn/policy/ai.html"
