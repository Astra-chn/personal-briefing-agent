from src.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from src.models import ScoredItem
from src.renderers.markdown_renderer import render_markdown


def test_markdown_renderer_includes_china_policy_section():
    markdown = render_markdown(
        "daily",
        "2026-06-21",
        [
            ScoredItem(
                title="中国人工智能政策更新",
                url="https://www.gov.cn/policy/ai.html",
                source="中国政府网",
                summary="政策关注人工智能和数字经济。",
                category="china_policy",
                keywords=["人工智能", "数字经济"],
                score=4.2,
            )
        ],
    )

    assert "## 五、中国国家政策" in markdown
    assert "中国人工智能政策更新" in markdown


def test_prompt_warns_not_to_invent_policy_from_other_sources():
    prompt = build_user_prompt("daily", "2026-06-21", [])

    assert "不要用 GitHub/AI 新闻硬凑国际或政策结论" in SYSTEM_PROMPT
    assert "中国国家政策" in prompt
