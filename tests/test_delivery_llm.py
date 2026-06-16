from types import SimpleNamespace

from src.delivery.email_sender import send_email
from src.llm.deepseek_client import DeepSeekClient


def test_deepseek_without_api_key_returns_none():
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)
    client = DeepSeekClient({"llm": {}}, logger)

    assert client.generate_briefing("daily", "2026-06-16", []) is None


def test_email_with_incomplete_settings_returns_false():
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    sent = send_email({"delivery": {"email_enabled": True}}, "Subject", "<p>Body</p>", None, logger)

    assert sent is False
