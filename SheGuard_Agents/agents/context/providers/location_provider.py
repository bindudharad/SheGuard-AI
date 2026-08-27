"""Provider for location data: reads from database (LiveLocation, TrackingSession, CCTVCamera).

This provider uses SQLAlchemy to connect directly to the existing sheguard.db. It does
not require the backend server to be running.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from agents.context.schemas import LocationContext, LocationStatus
from agents.context.exceptions import ProviderError
from agents.context.utils.validation import validate_coordinates
from agents.context.utils.time_utils import age_seconds, utcnow


class LocationProvider:
    """Fetches the best available location for an event."""

    def __init__(self, db_path: Optional[str] = None, stale_seconds: int = 600):
        self.db_path = db_path or self._default_db_path()
        self.stale_seconds = stale_seconds
        self._engine = None

    def _default_db_path(self) -> str:
        candidates = [
            os.environ.get("SHEGUARD_DB_PATH"),
            os.path.join(os.getcwd(), "sheguard.db"),
            os.path.join(os.getcwd(), "SheGuard_Backend", "sheguard.db"),
            r"C:\Programs\codex\SheGuard\SheGuard_Backend\sheguard.db",
            r"C:\Programs\codex\SheGuard\sheguard.db",
        ]
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return r"C:\Programs\codex\SheGuard\SheGuard_Backend\sheguard.db"

    def _get_engine(self):
        if self._engine is None:
            url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(url, connect_args={"check_same_thread": False})
        return self._engine

    def get_location(
        self,
        *,
        explicit_lat: Optional[float] = None,
        explicit_lon: Optional[float] = None,
        explicit_source: Optional[str] = None,
        explicit_ts: Optional[datetime] = None,
        camera_id: Optional[str] = None,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ) -> LocationContext:
        # 1. Explicit coordinates
        lat, lon = validate_coordinates(explicit_lat, explicit_lon)
        if lat is not None and lon is not None:
            return LocationContext(
                latitude=lat,
                longitude=lon,
                source=explicit_source or "explicit",
                confidence=0.95,
                status=LocationStatus.CURRENT,
            )

        # 2. Camera location
        if camera_id:
            cam_loc = self._camera_location(camera_id)
            if cam_loc:
                lat, lon, conf = cam_loc
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    source=f"camera:{camera_id}",
                    confidence=conf,
                    status=LocationStatus.CURRENT,
                )

        # 3. User\'s latest LiveLocation
        if user_id:
            ll = self._latest_live_location(user_id)
            if ll:
                lat, lon, ts = ll
                age = age_seconds(ts) or 0
                status = LocationStatus.STALE if age > self.stale_seconds else LocationStatus.CURRENT
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    source="live_location",
                    confidence=max(0.3, 0.9 - age / 3600.0),
                    status=status,
                )

        # 4. Tracking session
        if session_id:
            ts_loc = self._tracking_session_location(session_id)
            if ts_loc:
                lat, lon, ts = ts_loc
                age = age_seconds(ts) or 0
                status = LocationStatus.STALE if age > self.stale_seconds else LocationStatus.CURRENT
                return LocationContext(
                    latitude=lat,
                    longitude=lon,
                    source=f"tracking:{session_id}",
                    confidence=max(0.3, 0.85 - age / 3600.0),
                    status=status,
                )

        return LocationContext(status=LocationStatus.UNKNOWN)

    def _camera_location(self, camera_id: str) -> Optional[tuple[float, float, float]]:
        try:
            with Session(self._get_engine()) as db:
                if camera_id.isdigit():
                    row = db.execute(text("SELECT latitude, longitude FROM cctv_cameras WHERE camera_id = :id"), {"id": int(camera_id)}).fetchone()
                else:
                    row = db.execute(text("SELECT latitude, longitude FROM cctv_cameras WHERE camera_name = :name"), {"name": camera_id}).fetchone()
                if row and row[0] is not None and row[1] is not None:
                    return (row[0], row[1], 0.9)
        except Exception as e:
            raise ProviderError("camera_location", str(e), {"camera_id": camera_id})
        return None

    def _latest_live_location(self, user_id: int) -> Optional[tuple[float, float, datetime]]:
        try:
            with Session(self._get_engine()) as db:
                row = db.execute(text("SELECT latitude, longitude, timestamp FROM live_locations WHERE user_id = :uid ORDER BY timestamp DESC LIMIT 1"), {"uid": user_id}).fetchone()
                if row and row[0] is not None and row[1] is not None:
                    return (row[0], row[1], row[2])
        except Exception as e:
            raise ProviderError("live_location", str(e), {"user_id": user_id})
        return None

    def _tracking_session_location(self, session_id: str) -> Optional[tuple[float, float, datetime]]:
        try:
            with Session(self._get_engine()) as db:
                row = db.execute(text("SELECT last_latitude, last_longitude, last_update_at FROM tracking_sessions WHERE session_id = :sid"), {"sid": session_id}).fetchone()
                if row and row[0] is not None and row[1] is not None:
                    ts = row[2]
                    return (row[0], row[1], ts)
        except Exception as e:
            raise ProviderError("tracking_session", str(e), {"session_id": session_id})
        return None
