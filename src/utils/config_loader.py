from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is a declared dependency.
    load_dotenv = None


DEFAULT_CONFIG_PATH = Path("config.yaml")


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config_path = Path(path)
    if load_dotenv:
        load_dotenv(config_path.with_name(".env"))

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    config = _with_env_overrides(config)
    return config


def _with_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(config)

    _set_if_env(result, ("llm", "base_url"), "DEEPSEEK_BASE_URL")
    _set_if_env(result, ("llm", "model"), "DEEPSEEK_MODEL")
    _set_if_env(result, ("llm", "api_key"), "DEEPSEEK_API_KEY")
    _set_if_env(result, ("github", "token"), "GITHUB_TOKEN")
    _set_if_env(result, ("delivery", "smtp_host"), "SMTP_HOST")
    _set_if_env(result, ("delivery", "smtp_port"), "SMTP_PORT", cast=int)
    _set_if_env(result, ("delivery", "smtp_user"), "SMTP_USER")
    _set_if_env(result, ("delivery", "smtp_password"), "SMTP_PASSWORD")
    _set_if_env(result, ("delivery", "email_to"), "BRIEFING_EMAIL_TO")

    return result


def _set_if_env(
    config: dict[str, Any],
    path: tuple[str, ...],
    env_name: str,
    cast: type | None = None,
) -> None:
    value = os.getenv(env_name)
    if value in (None, ""):
        return
    if cast:
        try:
            value = cast(value)
        except ValueError:
            return

    cursor = config
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = value
