from src.models import ContentItem
from src.processors.cleaner import clean_items
from src.processors.deduplicator import canonicalize_url, deduplicate_items
from src.processors.scorer import filter_items, score_items


def test_clean_deduplicate_and_score_items():
    items = [
        ContentItem(
            title=" <b>AI Agent Tool</b> ",
            url="https://example.com/item?utm_source=test",
            source="Feed",
            summary="<p>Python RAG tutorial</p>",
            category="ai_news",
            keywords=["AI Agent"],
        ),
        ContentItem(
            title="AI Agent Tool",
            url="https://example.com/item?utm_campaign=x",
            source="Other",
            summary="Longer Python RAG tutorial summary",
            category="ai_news",
            keywords=["RAG"],
        ),
    ]
    config = {
        "profile": {"user_goal": "AI Agent RAG Python"},
        "ai_news": {"keywords": ["AI Agent", "RAG", "Python"]},
        "briefing": {"daily_max_items": 5},
        "scoring": {"min_score": 1.0},
    }

    cleaned = clean_items(items)
    deduped = deduplicate_items(cleaned)
    scored = score_items(deduped, config)
    filtered = filter_items(scored, config, "daily")

    assert len(deduped) == 1
    assert deduped[0].summary == "Longer Python RAG tutorial summary"
    assert filtered[0].score >= 1.0


def test_canonicalize_url_removes_tracking_parameters():
    assert canonicalize_url("https://EXAMPLE.com/a/?utm_source=x&keep=1#section") == "https://example.com/a?keep=1"


def test_filter_items_keeps_world_news_minimum_even_below_threshold():
    config = {
        "briefing": {
            "daily_max_items": 5,
            "category_minimums": {"world_news": 1},
        },
        "scoring": {"min_score": 4.5},
    }
    items = score_items(
        [
            ContentItem(
                title="AI Agent launch",
                url="https://example.com/ai",
                source="AI",
                summary="OpenAI Agent release",
                category="ai_news",
                keywords=["OpenAI"],
            ),
            ContentItem(
                title="Technology policy talks",
                url="https://example.com/world",
                source="World",
                summary="Policy and global economy update",
                category="world_news",
                keywords=["policy"],
            ),
        ],
        {
            "profile": {"user_goal": "AI Agent"},
            "ai_news": {"keywords": ["AI Agent", "OpenAI"]},
            "world_news": {"keywords": ["policy"]},
            "scoring": config["scoring"],
        },
    )

    filtered = filter_items(items, config, "daily")

    assert any(item.category == "world_news" for item in filtered)
