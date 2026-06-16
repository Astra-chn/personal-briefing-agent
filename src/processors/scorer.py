from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models import ContentItem, ScoredItem


ACTION_KEYWORDS = (
    "tutorial",
    "guide",
    "course",
    "github",
    "open source",
    "agent",
    "rag",
    "python",
    "java",
    "mcp",
    "学习",
    "开源",
    "工具",
    "自动化",
)
IMPORTANT_KEYWORDS = (
    "release",
    "launch",
    "regulation",
    "policy",
    "security",
    "semiconductor",
    "model",
    "funding",
    "监管",
    "政策",
    "半导体",
    "模型",
    "发布",
)


def score_items(items: list[ContentItem], config: dict[str, Any]) -> list[ScoredItem]:
    scoring_config = config.get("scoring", {})
    weights = {
        "relevance": float(scoring_config.get("relevance_weight", 0.4)),
        "importance": float(scoring_config.get("importance_weight", 0.3)),
        "novelty": float(scoring_config.get("novelty_weight", 0.2)),
        "actionability": float(scoring_config.get("actionability_weight", 0.1)),
    }
    interest_keywords = _interest_keywords(config)

    scored: list[ScoredItem] = []
    for item in items:
        details = {
            "relevance": _relevance_score(item, interest_keywords),
            "importance": _importance_score(item),
            "novelty": _novelty_score(item),
            "actionability": _keyword_score(item, ACTION_KEYWORDS),
        }
        total = sum(details[name] * weight for name, weight in weights.items())
        scored.append(
            ScoredItem(
                title=item.title,
                url=item.url,
                source=item.source,
                published_at=item.published_at,
                summary=item.summary,
                category=item.category,
                keywords=item.keywords,
                references=item.references,
                metadata=item.metadata,
                score=round(total, 2),
                score_details={key: round(value, 2) for key, value in details.items()},
            )
        )

    return sorted(scored, key=lambda item: item.score, reverse=True)


def filter_items(items: list[ScoredItem], config: dict[str, Any], mode: str) -> list[ScoredItem]:
    min_score = float(config.get("scoring", {}).get("min_score", 3.5))
    limit_key = "weekly_max_items" if mode == "weekly" else "daily_max_items"
    max_items = int(config.get("briefing", {}).get(limit_key, 12))
    selected = [item for item in items if item.score >= min_score]
    selected = _with_category_minimums(selected, items, config)
    if not selected:
        selected = items[:max_items]
    return _cap_items(selected, max_items)


def _with_category_minimums(
    selected: list[ScoredItem],
    all_items: list[ScoredItem],
    config: dict[str, Any],
) -> list[ScoredItem]:
    minimums = config.get("briefing", {}).get(
        "category_minimums",
        {"github": 2, "ai_news": 3, "world_news": 2},
    )
    result = list(selected)
    selected_urls = {item.url for item in result}

    for category, minimum in minimums.items():
        current_count = sum(1 for item in result if item.category == category)
        if current_count >= int(minimum):
            continue
        candidates = [
            item
            for item in all_items
            if item.category == category and item.url not in selected_urls
        ]
        for item in candidates[: max(0, int(minimum) - current_count)]:
            result.append(item)
            selected_urls.add(item.url)

    return sorted(result, key=lambda item: item.score, reverse=True)


def _cap_items(items: list[ScoredItem], max_items: int) -> list[ScoredItem]:
    if len(items) <= max_items:
        return items
    return sorted(items, key=lambda item: item.score, reverse=True)[:max_items]


def _interest_keywords(config: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    for section in ("github", "ai_news", "world_news"):
        section_config = config.get(section, {})
        keywords.extend(section_config.get("keywords", []))
        keywords.extend(section_config.get("topics", []))
    goal = config.get("profile", {}).get("user_goal", "")
    keywords.extend(str(goal).replace("、", " ").replace(",", " ").split())
    return sorted({keyword.lower() for keyword in keywords if keyword})


def _relevance_score(item: ContentItem, keywords: list[str]) -> float:
    text = _item_text(item)
    matches = sum(1 for keyword in keywords if keyword.lower() in text)
    if item.category == "github":
        matches += 1
    return min(5.0, 2.0 + matches * 0.7)


def _importance_score(item: ContentItem) -> float:
    score = _keyword_score(item, IMPORTANT_KEYWORDS)
    stars = int(item.metadata.get("stars", 0) or 0)
    if stars >= 5000:
        score = max(score, 5.0)
    elif stars >= 1000:
        score = max(score, 4.5)
    elif stars >= 200:
        score = max(score, 4.0)
    return score


def _novelty_score(item: ContentItem) -> float:
    if not item.published_at:
        return 3.0
    try:
        published = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
    except ValueError:
        return 3.0
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - published.astimezone(timezone.utc)).days
    if age_days <= 1:
        return 5.0
    if age_days <= 3:
        return 4.5
    if age_days <= 7:
        return 4.0
    if age_days <= 14:
        return 3.5
    return 2.5


def _keyword_score(item: ContentItem, keywords: tuple[str, ...]) -> float:
    text = _item_text(item)
    matches = sum(1 for keyword in keywords if keyword.lower() in text)
    return min(5.0, 2.5 + matches * 0.8)


def _item_text(item: ContentItem) -> str:
    return f"{item.title} {item.summary} {' '.join(item.keywords)}".lower()
