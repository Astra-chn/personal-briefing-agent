from argparse import Namespace

import main


def test_main_dry_run_generates_files(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
profile:
  user_goal: AI Agent RAG Python
briefing:
  daily_max_items: 12
  weekly_max_items: 25
llm:
  model: deepseek-v4-flash
github:
  enabled: false
ai_news:
  enabled: false
world_news:
  enabled: false
scoring:
  relevance_weight: 0.4
  importance_weight: 0.3
  novelty_weight: 0.2
  actionability_weight: 0.1
  min_score: 1.0
output:
  save_markdown: true
  save_html: true
  save_to_sqlite: true
  markdown_dir: output
  database_path: data/briefing.db
delivery:
  email_enabled: false
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "ROOT", tmp_path)

    result = main.run(Namespace(mode="daily", config=str(config_path), dry_run=True, no_email=True))

    assert result.markdown_path
    assert result.html_path
    assert result.item_count > 0
    assert (tmp_path / "output" / "daily").exists()
