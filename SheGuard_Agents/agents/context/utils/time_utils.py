
"""Time utilities for the Context Agent.

All timestamps are timezone-aware. The default timezone is configurable and must
not be hard-coded to a single region.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def get_tz(timezone_name: str = "UTC"):
    if ZoneInfo is None:
        raise RuntimeError("zoneinfo is not available in this Python build")
    try:
        return ZoneInfo(timezone_name)
    except Exception as exc:  # pragma: no cover
        raise ValueError(f"Invalid timezone: {timezone_name}") from exc


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_local(dt: datetime, timezone_name: str = "UTC") -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_tz(timezone_name))


def now_local(timezone_name: str = "UTC") -> datetime:
    return utcnow().astimezone(get_tz(timezone_name))


def parse_time_string(value: str) -> time:
    """Parse HH:MM into a time object (24-hour, timezone-naive)."""
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def is_night(
    dt: datetime,
    night_start: str = "22:00",
    night_end: str = "05:00",
) -> bool:
    """Return True if local time is within the configured night window.

    Night windows may cross midnight (e.g. 22:00 -> 05:00). This only flags a
    *time period*, never a danger level.
    """
    local = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    t = local.time()
    start = parse_time_string(night_start)
    end = parse_time_string(night_end)
    if start <= end:
        return start <= t < end
    # window crosses midnight
    return t >= start or t < end


def classify_period(
    dt: datetime,
    night_start: str = "22:00",
    night_end: str = "05:00",
) -> str:
    """Classify time into a contextual period.

    This is a contextual factor only. It never asserts danger.
    """
    local = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    t = local.time()
    start = parse_time_string(night_start)
    end = parse_time_string(night_end)
    late_start = parse_time_string("00:00")
    if is_night(local, night_start, night_end):
        if t < end:
            return "late_night"
        return "night"
    if time(17, 0) <= t < time(20, 0):
        return "evening"
    if time(20, 0) <= t < start:
        return "evening"
    return "day"


def is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


def day_of_week(dt: datetime) -> str:
    return dt.strftime("%A")


def age_seconds(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    ref = utcnow()
    other = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    return (ref - other).total_seconds()
