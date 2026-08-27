"""Provider for incident history: reads from incidents table."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from agents.context.schemas import HistoryContext, DataStatus
from agents.context.exceptions import ProviderError
from agents.context.analyzers.history_analyzer import IncidentRecord
from agents.context.utils.time_utils import utcnow


class IncidentProvider:
    """Queries historical incidents from the database with optional spatial/temporal filtering."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or r"C:\Programs\codex\SheGuard\SheGuard_Backend\sheguard.db"
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(url, connect_args={"check_same_thread": False})
        return self._engine

    def get_recent(
        self,
        *,
        lookback_hours: int = 24,
        limit: int = 100,
        ref_lat: Optional[float] = None,
        ref_lon: Optional[float] = None,
        radius_meters: Optional[int] = None,
    ) -> List[IncidentRecord]:
        try:
            cutoff = utcnow() - timedelta(hours=lookback_hours)
            with Session(self._get_engine()) as db:
                rows = db.execute(text("SELECT incident_id, created_at, latitude, longitude, incident_type, threat_score, status FROM incidents WHERE created_at >= :cutoff ORDER BY created_at DESC LIMIT :limit"), {"cutoff": cutoff, "limit": limit}).fetchall()
                records = []
                for row in rows:
                    records.append(IncidentRecord(
                        incident_id=row[0],
                        created_at=row[1] if isinstance(row[1], datetime) else datetime.fromisoformat(row[1]) if row[1] else utcnow(),
                        latitude=row[2],
                        longitude=row[3],
                        incident_type=row[4],
                        severity=row[5] / 10.0 if row[5] else 0.5,
                        status=row[6],
                    ))
                return records
        except Exception as e:
            raise ProviderError("incident_history", str(e))

    def get_nearby(
        self,
        lat: float,
        lon: float,
        *,
        radius_meters: int = 500,
        lookback_hours: int = 24,
        limit: int = 100,
    ) -> List[IncidentRecord]:
        all_recent = self.get_recent(lookback_hours=lookback_hours, limit=limit)
        from agents.context.utils.geo import haversine_distance_meters
        nearby = []
        for rec in all_recent:
            if rec.latitude is not None and rec.longitude is not None:
                dist = haversine_distance_meters(lat, lon, rec.latitude, rec.longitude)
                if dist <= radius_meters:
                    nearby.append(rec)
        return nearby
