
"""Provider for time/date information (timezone-aware)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from agents.context.utils.time_utils import utcnow, to_local, classify_period, day_of_week, is_weekend
from agents.context.schemas import TimeContext, TimePeriod


class TimeProvider:
    """Provides timezone-aware timestamps and time context."""

    def __init__(self, default_timezone: str = "Asia/Kolkata"):
        self.default_timezone = default_timezone

    def now(self, timezone_name: Optional[str] = None) -> datetime:
        return utcnow().astimezone(timezone_name or self.default_timezone)

    def analyze(self, dt: Optional[datetime] = None, timezone_name: Optional[str] = None) -> TimeContext:
        tz = timezone_name or self.default_timezone
        if dt is None:
            dt = utcnow()
        local = to_local(dt, tz)
        return TimeContext(
            local=local.strftime("%H:%M"),
            period=TimePeriod(classify_period(local)),
            day_of_week=day_of_week(local),
            is_weekend=is_weekend(local),
            hour=local.hour,
            timezone=tz,
        )
