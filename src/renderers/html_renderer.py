from __future__ import annotations

import html

try:
    import markdown as markdown_lib
except ImportError:  # pragma: no cover - declared dependency, defensive fallback.
    markdown_lib = None


STYLE = """
body {
  margin: 0;
  padding: 24px;
  background: #f6f7f9;
  color: #1f2933;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  line-height: 1.65;
}
.container {
  max-width: 860px;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 28px;
}
h1, h2, h3 { color: #111827; line-height: 1.3; }
a { color: #2563eb; }
blockquote {
  margin: 16px 0;
  padding: 12px 16px;
  background: #f8fafc;
  border-left: 4px solid #94a3b8;
}
code { background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }
"""


def render_html(markdown_text: str) -> str:
    if markdown_lib:
        body = markdown_lib.markdown(markdown_text, extensions=["extra", "sane_lists"])
    else:
        body = _simple_markdown_to_html(markdown_text)
    return f"<!doctype html><html><head><meta charset=\"utf-8\"><style>{STYLE}</style></head><body><main class=\"container\">{body}</main></body></html>"


def _simple_markdown_to_html(markdown_text: str) -> str:
    lines = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        escaped = html.escape(line)
        if line.startswith("# "):
            lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            lines.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            lines.append(f"<p>{escaped}</p>")
        else:
            lines.append(f"<p>{escaped}</p>")
    return "\n".join(lines)
