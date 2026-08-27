from __future__ import annotations

import math
from dataclasses import dataclass


EARTH_RADIUS_METERS = 6371000.0


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float


def haversine_distance_meters(a: GeoPoint, b: GeoPoint) -> float:
    lat1 = math.radians(a.latitude)
    lat2 = math.radians(b.latitude)
    dlat = lat2 - lat1
    dlng = math.radians(b.longitude - a.longitude)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(value)))


def has_coordinates(latitude: float | None, longitude: float | None) -> bool:
    return latitude is not None and longitude is not None
