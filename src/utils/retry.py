from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar


T = TypeVar("T")


def retry(
    func: Callable[[], T],
    attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff: float = 2.0,
) -> T:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return func()
        except Exception as error:  # noqa: BLE001 - helper intentionally retries broad failures.
            last_error = error
            if attempt == attempts - 1:
                break
            time.sleep(delay_seconds * (backoff**attempt))
    assert last_error is not None
    raise last_error
