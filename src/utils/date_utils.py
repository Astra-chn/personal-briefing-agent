from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def now_beijing() -> datetime:
    return datetime.now(BEIJING_TZ)


def resolve_mode(mode: str, now: datetime | None = None) -> str:
    if mode in {"daily", "weekly"}:
        return mode
    if mode != "auto":
        raise ValueError("mode must be daily, weekly, or auto")

    current = now or now_beijing()
    # The workflow has a daily morning trigger and a weekly Sunday evening trigger.
    if current.weekday() == 6 and current.hour >= 18:
        return "weekly"
    return "daily"


def date_label_for_mode(mode: str, now: datetime | None = None) -> str:
    current = now or now_beijing()
    if mode == "weekly":
        year, week, _ = current.isocalendar()
        return f"{year}-W{week:02d}"
    return current.strftime("%Y-%m-%d")
