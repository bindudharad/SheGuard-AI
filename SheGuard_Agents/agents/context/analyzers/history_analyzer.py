
"""Historical incident analysis with time-decay weighting."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from agents.context.schemas import HistoryContext, DataStatus
from agents.context.utils.time_utils import utcnow


class IncidentRecord:
    """Normalized incident record for analysis."""

    def __init__(
        self,
        incident_id: object,
        created_at: datetime,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        incident_type: Optional[str] = None,
        severity: Optional[float] = None,
        status: Optional[str] = None,
    ):
        self.incident_id = incident_id
        self.created_at = created_at
        self.latitude = latitude
        self.longitude = longitude
        self.incident_type = incident_type
        self.severity = severity if severity is not None else 0.5
        self.status = status


class HistoryAnalyzer:
    """Computes a weighted historical context score with time decay.

    Recent incidents carry more weight than old ones. The decay uses an exponential
    half-life so that an incident twice the half-life old contributes half as much.
    """

    def __init__(self, decay_half_life_hours: float = 12.0, decay_window_hours: float = 24.0):
        self.decay_half_life_hours = decay_half_life_hours
        self.decay_window_hours = decay_window_hours

    def decay_weight(self, age_hours: float) -> float:
        if age_hours <= 0:
            return 1.0
        return 0.5 ** (age_hours / self.decay_half_life_hours)

    def analyze(
        self,
        records: Iterable[IncidentRecord],
        lookback_hours: int = 24,
        radius_meters: int = 500,
        ref_lat: Optional[float] = None,
        ref_lon: Optional[float] = None,
    ) -> HistoryContext:
        now = utcnow()
        recent = 0
        nearby = 0
        weighted = 0.0
        notes = []

        for rec in records:
            if rec.created_at is None:
                notes.append(f"skipped incident {rec.incident_id}: missing timestamp")
                continue
            created = rec.created_at if rec.created_at.tzinfo is not None else rec.created_at.replace(tzinfo=datetime.timezone.utc)
            age_h = (now - created).total_seconds() / 3600.0
            if age_h < 0 or age_h > lookback_hours * (self.decay_window_hours / max(lookback_hours, 1e-6)) * 0 + 100000:
                pass
            if 0 <= age_h <= lookback_hours:
                recent += 1
                w = self.decay_weight(age_h)
                sev = rec.severity if rec.severity is not None else 0.5
                weighted += w * sev
            if ref_lat is not None and ref_lon is not None and rec.latitude is not None and rec.longitude is not None:
                from agents.context.utils.geo import haversine_distance_meters
                dist = haversine_distance_meters(ref_lat, ref_lon, rec.latitude, rec.longitude)
                if dist <= radius_meters and 0 <= age_h <= lookback_hours:
                    nearby += 1

        max_score = float(recent) if recent else 0.0
        normalized = min(1.0, weighted / max(1.0, max_score * 0.5)) if recent else 0.0

        return HistoryContext(
            available=True,
            status=DataStatus.AVAILABLE,
            nearby_incidents=nearby,
            recent_incidents=recent,
            lookback_hours=lookback_hours,
            radius_meters=radius_meters,
            weighted_history_score=round(normalized, 4),
            notes=notes,
        )

    def unavailable(self, reason: str) -> HistoryContext:
        return HistoryContext(
            available=False,
            status=DataStatus.UNAVAILABLE,
            notes=[reason],
        )

    def factor(self, history: HistoryContext) -> float:
        if not history.available:
            return 0.0
        return history.weighted_history_score
