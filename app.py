from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"


def list_briefings(mode: str) -> list[Path]:
    directory = OUTPUT_DIR / mode
    if not directory.exists():
        return []
    return sorted(directory.glob("*.md"), reverse=True)


def main() -> None:
    st.set_page_config(page_title="个人 AI 简报助手", layout="wide")
    st.title("个人 AI 简报助手")

    mode_label = st.sidebar.radio("简报类型", ["每日简报", "每周简报"])
    mode = "daily" if mode_label == "每日简报" else "weekly"
    files = list_briefings(mode)

    if not files:
        st.info("还没有生成简报。可以先运行 `python main.py --mode daily --dry-run`。")
        return

    selected = st.sidebar.selectbox("历史简报", files, format_func=lambda p: p.stem)
    markdown_text = selected.read_text(encoding="utf-8")

    st.caption(str(selected.relative_to(ROOT)))
    tab_preview, tab_raw = st.tabs(["阅读", "Markdown 原文"])
    with tab_preview:
        st.markdown(markdown_text)
    with tab_raw:
        st.code(markdown_text, language="markdown")


if __name__ == "__main__":
    main()
