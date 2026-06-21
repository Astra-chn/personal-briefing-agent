from __future__ import annotations

from src.models import ScoredItem


SECTION_TITLES = {
    "github": "GitHub 热门项目",
    "ai_news": "AI 发展动态",
    "world_news": "国际形势",
    "china_policy": "中国国家政策",
}


def render_markdown(
    mode: str,
    date_label: str,
    items: list[ScoredItem],
    llm_summary: str | None = None,
) -> str:
    if mode == "weekly":
        return _render_weekly(date_label, items, llm_summary)
    return _render_daily(date_label, items, llm_summary)


def _render_daily(date_label: str, items: list[ScoredItem], llm_summary: str | None) -> str:
    lines = [f"# 每日个人简报 - {date_label}", ""]
    lines.extend(_summary_block(llm_summary))
    lines.extend(["## 一、今日最值得关注的 5 件事", ""])
    for item in items[:5]:
        lines.append(f"- **{item.title}**（{item.source}，评分 {item.score}）：{_short_reason(item)}")
    if not items:
        lines.append("- 暂无可用内容。")
    lines.append("")

    lines.extend(
        _category_sections(
            [
                ("github", "## 二、GitHub 热门项目"),
                ("ai_news", "## 三、AI 发展动态"),
                ("world_news", "## 四、国际形势"),
                ("china_policy", "## 五、中国国家政策"),
            ],
            items,
        )
    )
    lines.extend(_personal_advice(items, heading="## 六、对我的个人建议"))
    lines.extend(_source_links(items, heading="## 七、来源链接"))
    return "\n".join(lines).strip() + "\n"


def _render_weekly(date_label: str, items: list[ScoredItem], llm_summary: str | None) -> str:
    lines = [f"# 每周个人简报 - {date_label}", ""]
    lines.extend(_summary_block(llm_summary))
    lines.extend(["## 一、本周最重要的趋势", ""])
    for item in items[:6]:
        lines.append(f"- **{item.title}**：{_short_reason(item)}")
    if not items:
        lines.append("- 暂无可用内容。")
    lines.append("")

    lines.extend(
        _category_sections(
            [
                ("github", "## 二、GitHub 开源趋势"),
                ("ai_news", "## 三、AI 行业趋势"),
                ("world_news", "## 四、国际形势趋势"),
                ("china_policy", "## 五、中国政策观察"),
            ],
            items,
        )
    )
    lines.extend(_personal_advice(items, heading="## 六、对我的启发"))
    lines.extend(_watchlist(items))
    lines.extend(_source_links(items, heading="## 八、来源链接"))
    return "\n".join(lines).strip() + "\n"


def _summary_block(llm_summary: str | None) -> list[str]:
    if not llm_summary:
        return [
            "> DeepSeek 总结暂时不可用，以下为规则模板生成的基础版简报。",
            "",
        ]
    return ["## AI 生成综述", "", llm_summary.strip(), ""]


def _category_sections(
    sections: list[tuple[str, str]],
    items: list[ScoredItem],
) -> list[str]:
    lines: list[str] = []
    for category, heading in sections:
        lines.extend([heading, "", *_items_for_category(items, category)])
    return lines


def _items_for_category(items: list[ScoredItem], category: str) -> list[str]:
    filtered = [item for item in items if item.category == category]
    if not filtered:
        return ["- 暂无高分内容。", ""]

    lines: list[str] = []
    for item in filtered:
        lines.extend(
            [
                f"### {item.title}",
                "",
                f"- 来源：{item.source}",
                f"- 链接：{item.url}",
                f"- 评分：{item.score}",
                f"- 简介：{item.summary or '无摘要'}",
                f"- 为什么值得关注：{_short_reason(item)}",
                "",
            ]
        )
    return lines


def _personal_advice(items: list[ScoredItem], heading: str) -> list[str]:
    github_items = [item for item in items if item.category == "github"]
    policy_or_world_items = [
        item for item in items if item.category in {"world_news", "china_policy"}
    ]
    ai_items = [item for item in items if item.category == "ai_news"]
    reading_item = (policy_or_world_items or ai_items or github_items or [None])[0]
    project_item = (github_items or ai_items or policy_or_world_items or [None])[0]

    advice = [
        heading,
        "",
        f"1. 优先拆解：{project_item.title if project_item else '本期暂无合适项目'}。",
        f"2. 重点阅读：{reading_item.title if reading_item else '本期暂无高价值国际/政策内容'}。",
        "3. 把国际新闻或政策术语整理成申论/面试素材，同时把技术方向转成一个小项目或读书笔记。",
        "",
    ]
    return advice


def _watchlist(items: list[ScoredItem]) -> list[str]:
    keywords = []
    for item in items:
        keywords.extend(item.keywords)
    top_keywords = list(dict.fromkeys(keywords))[:6]
    if not top_keywords:
        top_keywords = ["AI Agent", "RAG", "MCP", "半导体", "AI 监管", "新质生产力"]
    return ["## 七、下周关注清单", "", *[f"- {keyword}" for keyword in top_keywords], ""]


def _source_links(items: list[ScoredItem], heading: str) -> list[str]:
    lines = [heading, ""]
    if not items:
        return lines + ["- 暂无来源。", ""]
    for item in items:
        lines.append(f"- [{item.title}]({item.url}) - {item.source}")
        for ref in item.references:
            lines.append(f"  - 参考来源：{ref}")
    lines.append("")
    return lines


def _short_reason(item: ScoredItem) -> str:
    if item.category == "github":
        language = item.metadata.get("language", "Unknown")
        stars = item.metadata.get("stars", 0)
        return f"{language} 项目，Stars {stars}，适合评估是否能拆成练手项目。"
    if item.category == "china_policy":
        if item.keywords:
            return f"命中政策关键词 {'、'.join(item.keywords[:3])}，适合积累公考、申论和科技政策素材。"
        return "来自国家政策官网，可用于观察国内科技、就业和产业政策方向。"
    if item.category == "world_news":
        if item.keywords:
            return f"命中国际关键词 {'、'.join(item.keywords[:3])}，有助于判断外部环境和科技政策变化。"
        return "国际新闻来源，可用于补充全球政治、经济和科技政策视角。"
    if item.keywords:
        return f"命中关键词 {'、'.join(item.keywords[:3])}，可能影响学习方向或技术判断。"
    return item.summary[:80] or "该条目综合评分较高，值得快速浏览。"
