from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from src.collectors.github_collector import GitHubCollector
from src.collectors.rss_collector import RSSCollector
from src.llm.deepseek_client import DeepSeekClient
from src.models import BriefingResult, ContentItem
from src.processors.cleaner import clean_items
from src.processors.deduplicator import deduplicate_items
from src.processors.scorer import filter_items, score_items
from src.renderers.html_renderer import render_html
from src.renderers.markdown_renderer import render_markdown
from src.storage.db import BriefingDB
from src.delivery.email_sender import send_email
from src.utils.config_loader import load_config
from src.utils.date_utils import date_label_for_mode, now_beijing, resolve_mode
from src.utils.logger import setup_logger


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate personal briefing.")
    parser.add_argument("--mode", choices=["daily", "weekly", "auto"], default="daily")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--dry-run", action="store_true", help="Use built-in sample data and skip network/email.")
    parser.add_argument("--no-email", action="store_true", help="Generate files without sending email.")
    return parser.parse_args()


def run(args: argparse.Namespace) -> BriefingResult:
    logger = setup_logger()
    config = load_config(args.config)
    current = now_beijing()
    mode = resolve_mode(args.mode, current)
    date_label = date_label_for_mode(mode, current)
    logger.info("Generating %s briefing for %s", mode, date_label)

    raw_items = _sample_items() if args.dry_run else _collect_items(config, logger)
    cleaned_items = clean_items(raw_items)
    unique_items = deduplicate_items(cleaned_items)
    scored_items = score_items(unique_items, config)
    selected_items = filter_items(scored_items, config, mode)

    db = _database(config, logger)
    if db:
        db.initialize()
        db.save_items(selected_items)

    llm_summary = None
    if not args.dry_run:
        llm_summary = DeepSeekClient(config, logger).generate_briefing(mode, date_label, selected_items)
    markdown_text = render_markdown(mode, date_label, selected_items, llm_summary)
    html_text = render_html(markdown_text)

    markdown_path, html_path = _write_outputs(config, mode, date_label, markdown_text, html_text)
    email_sent = False
    if not args.dry_run and not args.no_email:
        subject_prefix = "每周个人简报" if mode == "weekly" else "每日个人简报"
        email_sent = send_email(
            config,
            f"{subject_prefix} - {date_label}",
            html_text,
            str(markdown_path) if markdown_path else None,
            logger,
        )

    result = BriefingResult(
        mode=mode,
        date_label=date_label,
        markdown_path=str(markdown_path) if markdown_path else None,
        html_path=str(html_path) if html_path else None,
        item_count=len(selected_items),
        email_sent=email_sent,
        llm_used=bool(llm_summary),
    )
    if db:
        db.save_run(result)

    logger.info("Briefing generated: markdown=%s html=%s email_sent=%s", markdown_path, html_path, email_sent)
    return result


def _collect_items(config: dict[str, Any], logger) -> list[ContentItem]:
    items: list[ContentItem] = []

    try:
        items.extend(GitHubCollector(config, logger).collect())
    except Exception as error:  # noqa: BLE001 - top-level collection must stay fault tolerant.
        logger.warning("GitHub collection failed: %s", error)

    for section_name, category in (("ai_news", "ai_news"), ("world_news", "world_news")):
        try:
            items.extend(RSSCollector(config, section_name, category, logger).collect())
        except Exception as error:  # noqa: BLE001
            logger.warning("%s collection failed: %s", section_name, error)

    if not items:
        logger.warning("No external items collected; generating fallback sample briefing.")
        return _sample_items()
    return items


def _write_outputs(
    config: dict[str, Any],
    mode: str,
    date_label: str,
    markdown_text: str,
    html_text: str,
) -> tuple[Path | None, Path | None]:
    output_config = config.get("output", {})
    base_dir = ROOT / output_config.get("markdown_dir", "output") / mode
    base_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = base_dir / f"{date_label}.md" if output_config.get("save_markdown", True) else None
    html_path = base_dir / f"{date_label}.html" if output_config.get("save_html", True) else None

    if markdown_path:
        markdown_path.write_text(markdown_text, encoding="utf-8")
    if html_path:
        html_path.write_text(html_text, encoding="utf-8")
    return markdown_path, html_path


def _database(config: dict[str, Any], logger) -> BriefingDB | None:
    output_config = config.get("output", {})
    if not output_config.get("save_to_sqlite", True):
        return None
    return BriefingDB(ROOT / output_config.get("database_path", "data/briefing.db"), logger)


def _sample_items() -> list[ContentItem]:
    return [
        ContentItem(
            title="openai/codex-style-agent",
            url="https://github.com/example/codex-style-agent",
            source="GitHub",
            published_at=now_beijing().isoformat(),
            summary="一个演示 AI Coding Agent 工作流的开源项目，包含任务规划、工具调用和代码生成。",
            category="github",
            keywords=["AI Agent", "coding agent", "Python"],
            metadata={"stars": 3200, "forks": 210, "language": "Python"},
        ),
        ContentItem(
            title="DeepSeek 发布新的低成本推理模型 API",
            url="https://example.com/deepseek-model-news",
            source="Example AI News",
            published_at=now_beijing().isoformat(),
            summary="DeepSeek 更新模型服务，强调更低成本的文本总结和代码任务能力。",
            category="ai_news",
            keywords=["DeepSeek", "LLM", "AI Agent"],
        ),
        ContentItem(
            title="多国讨论 AI 监管与半导体供应链政策",
            url="https://example.com/ai-policy-semiconductor",
            source="Example World News",
            published_at=now_beijing().isoformat(),
            summary="科技政策和半导体供应链继续影响 AI 产业竞争格局。",
            category="world_news",
            keywords=["AI监管", "半导体", "科技政策"],
        ),
    ]


def main() -> None:
    result = run(parse_args())
    print(f"Markdown: {result.markdown_path}")
    print(f"HTML: {result.html_path}")
    print(f"Items: {result.item_count}")
    print(f"Email sent: {result.email_sent}")


if __name__ == "__main__":
    main()
