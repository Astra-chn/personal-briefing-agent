from __future__ import annotations

from src.models import ScoredItem


SYSTEM_PROMPT = """你是我的个人信息分析助手。
我的背景：
- 我是编程初学者，代码基础不强
- 我更适合通过项目学习
- 我关注 AI Agent、RAG、后端转 AI、自动化工具
- 我也关注公考、国际形势、科技政策
- 我希望简报不要堆砌新闻，而是告诉我什么值得关注、为什么重要、对我有什么用

要求：
1. 不要编造材料中没有的信息
2. 不要夸大新闻影响
3. 每条内容尽量保留来源链接
4. 对 GitHub 项目说明是否适合我学习
5. 对 AI 新闻说明趋势影响
6. 对国际形势说明和科技、就业、政策环境的关系
7. 最后给出具体行动建议
8. 语言直接、清晰、不要空话
"""


def build_user_prompt(mode: str, date_label: str, items: list[ScoredItem]) -> str:
    mode_name = "每周" if mode == "weekly" else "每日"
    lines = [
        f"请根据以下材料生成一份中文{mode_name}个人简报。",
        f"日期/周期：{date_label}",
        "",
        "材料：",
    ]
    for index, item in enumerate(items, start=1):
        lines.extend(
            [
                f"{index}. [{item.category}] {item.title}",
                f"   来源：{item.source}",
                f"   链接：{item.url}",
                f"   时间：{item.published_at or '未知'}",
                f"   评分：{item.score}",
                f"   摘要：{item.summary or '无摘要'}",
                "",
            ]
        )

    if mode == "weekly":
        lines.append("请输出：本周重要趋势、GitHub 开源趋势、AI 行业趋势、国际形势趋势、对我的启发、下周关注清单。")
    else:
        lines.append("请输出：今日最值得关注的 5 件事、GitHub 热门项目、AI 发展动态、国际形势与科技政策、对我的个人建议。")

    return "\n".join(lines)
