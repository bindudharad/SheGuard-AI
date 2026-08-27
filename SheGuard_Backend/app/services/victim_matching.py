from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LiveLocation, User
from app.services.emergency_config import settings
from app.services.geo import GeoPoint, haversine_distance_meters


@dataclass(frozen=True)
class VictimMatch:
    user: User
    location: LiveLocation
    distance_meters: float


class VictimMatchingEngine:
    def __init__(self, radius_meters: float | None = None, max_age_seconds: int | None = None) -> None:
        self.radius_meters = radius_meters or settings.incident_match_radius_meters
        self.max_age_seconds = max_age_seconds or settings.active_location_max_age_seconds

    def find_nearest_user(self, db: Session, latitude: float, longitude: float, exclude_user_id: int | None = None) -> VictimMatch | None:
        cutoff = datetime.utcnow() - timedelta(seconds=self.max_age_seconds)
        rows = db.scalars(
            select(LiveLocation)
            .where(LiveLocation.timestamp >= cutoff)
            .order_by(LiveLocation.timestamp.desc())
        ).all()
        incident_point = GeoPoint(latitude, longitude)
        latest_by_user: dict[int, LiveLocation] = {}
        for row in rows:
            if exclude_user_id is not None and row.user_id == exclude_user_id:
                continue
            latest_by_user.setdefault(row.user_id, row)

        nearest: VictimMatch | None = None
        for row in latest_by_user.values():
            user = db.get(User, row.user_id)
            if not user:
                continue
            distance = haversine_distance_meters(incident_point, GeoPoint(row.latitude, row.longitude))
            if distance <= self.radius_meters and (nearest is None or distance < nearest.distance_meters):
                nearest = VictimMatch(user=user, location=row, distance_meters=distance)
        return nearest
