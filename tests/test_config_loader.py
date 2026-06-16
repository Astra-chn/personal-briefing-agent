from pathlib import Path

from src.utils.config_loader import load_config


def test_env_overrides_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
llm:
  base_url: https://old.example.com
  model: old-model
delivery:
  smtp_port: 25
github: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("SMTP_PORT", "587")

    config = load_config(config_path)

    assert config["llm"]["model"] == "deepseek-v4-flash"
    assert config["delivery"]["smtp_port"] == 587
