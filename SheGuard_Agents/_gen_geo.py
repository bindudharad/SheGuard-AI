import base64, os

content = r'''
"""Utility functions for geospatial calculations used by the Context Agent.

Reuses the backend's haversine implementation when available, otherwise falls back
to a self-contained implementation so the agent does not hard-depend on the backend
package at import time.
"""

from __future__ import annotations

import math

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance between two lat/lon points in meters.

    This is the canonical haversine formula. It must NOT be replaced by naive
    Euclidean distance on lat/lon degrees.
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return EARTH_RADIUS_METERS * c


def point_in_circle(
    lat: float, lon: float, center_lat: float, center_lon: float, radius_m: float
) -> bool:
    """Whether a point is within a circular zone defined by center + radius."""
    return haversine_distance_meters(lat, lon, center_lat, center_lon) <= radius_m


def nearest_distance(
    lat: float, lon: float, points: list[tuple[float, float]]
) -> float | None:
    """Distance in meters to the nearest point, or None if no points."""
    if not points:
        return None
    return min(haversine_distance_meters(lat, lon, p[0], p[1]) for p in points)
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\utils\geo.py'
encoded = base64.b64encode(content.encode("utf-8"))
decoded = base64.b64decode(encoded)
with open(target, "wb") as f:
    f.write(decoded)
print("written", len(decoded), "bytes")