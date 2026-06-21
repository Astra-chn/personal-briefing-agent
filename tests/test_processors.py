from datetime import UTC, datetime

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


def test_filter_items_respects_category_maximums():
    config = {
        "briefing": {
            "daily_max_items": 6,
            "category_maximums": {"github": 2, "ai_news": 4},
        },
        "scoring": {"min_score": 1.0},
    }
    items = score_items(
        [
            ContentItem(
                title=f"repo-{index}",
                url=f"https://github.com/example/repo-{index}",
                source="GitHub",
                summary="AI Agent Python project",
                category="github",
                keywords=["AI Agent"],
                metadata={"stars": 10000, "language": "Python"},
            )
            for index in range(5)
        ]
        + [
            ContentItem(
                title="AI policy news",
                url="https://example.com/ai-news",
                source="AI",
                summary="OpenAI regulation policy",
                category="ai_news",
                keywords=["OpenAI"],
            )
        ],
        {"profile": {"user_goal": "AI Agent"}, "scoring": config["scoring"]},
    )

    filtered = filter_items(items, config, "daily")

    assert sum(1 for item in filtered if item.category == "github") == 2


def test_score_items_applies_history_repeat_penalty():
    item = ContentItem(
        title="langchain-ai/langchain",
        url="https://github.com/langchain-ai/langchain",
        source="GitHub",
        summary="AI Agent Python project",
        category="github",
        keywords=["AI Agent"],
        metadata={"stars": 10000, "language": "Python"},
    )
    config = {
        "profile": {"user_goal": "AI Agent"},
        "scoring": {"min_score": 1.0},
        "history": {
            "repeat_penalty_days": {"github": 7},
            "repeat_penalty_points": {"github": 1.4},
        },
    }

    baseline = score_items([item], config)[0]
    penalized = score_items(
        [item],
        config,
        history={
            item.url: {
                "last_selected_at": datetime.now(UTC).isoformat(),
                "seen_count": 4,
            }
        },
    )[0]

    assert penalized.score < baseline.score
    assert "repeat_penalty" in penalized.score_details
