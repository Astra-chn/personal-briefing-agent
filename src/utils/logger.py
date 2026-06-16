from __future__ import annotations

import logging
import os
from typing import Iterable


SENSITIVE_ENV_NAMES = (
    "DEEPSEEK_API_KEY",
    "GITHUB_TOKEN",
    "SMTP_PASSWORD",
)


class SecretRedactingFilter(logging.Filter):
    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self.secrets = [secret for secret in secrets if secret]

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "***")
        record.msg = message
        record.args = ()
        return True


def setup_logger(name: str = "briefing", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)

    secrets = [os.getenv(name) for name in SENSITIVE_ENV_NAMES]
    logger.addFilter(SecretRedactingFilter(secrets))
    return logger
