from __future__ import annotations

from typing import Any

from src.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from src.models import ScoredItem


class DeepSeekClient:
    def __init__(self, config: dict[str, Any], logger) -> None:
        self.config = config
        self.logger = logger
        self.llm_config = config.get("llm", {})

    def generate_briefing(self, mode: str, date_label: str, items: list[ScoredItem]) -> str | None:
        api_key = self.llm_config.get("api_key")
        if not api_key:
            self.logger.warning("DEEPSEEK_API_KEY is not configured; using fallback briefing.")
            return None

        try:
            from openai import OpenAI
        except ImportError:
            self.logger.warning("openai package is not installed; using fallback briefing.")
            return None

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=self.llm_config.get("base_url", "https://api.deepseek.com"),
                timeout=float(self.llm_config.get("timeout_seconds", 60)),
            )
            response = client.chat.completions.create(
                model=self.llm_config.get("model", "deepseek-v4-flash"),
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": build_user_prompt(mode, date_label, items)},
                ],
                temperature=float(self.llm_config.get("temperature", 0.3)),
                max_tokens=int(self.llm_config.get("max_tokens", 4000)),
            )
            content = response.choices[0].message.content
            return content.strip() if content else None
        except Exception as error:  # noqa: BLE001 - LLM failure must not fail the run.
            self.logger.warning("DeepSeek API call failed: %s", error)
            return None
