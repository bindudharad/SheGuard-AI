import base64, os

content = r'''
"""Validation helpers for Context Agent inputs."""

from __future__ import annotations

from typing import Optional, Tuple

from agents.context.exceptions import ValidationError

LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 180.0


def is_valid_latitude(lat: Optional[float]) -> bool:
    if lat is None:
        return False
    try:
        return LAT_MIN <= float(lat) <= LAT_MAX
    except (TypeError, ValueError):
        return False


def is_valid_longitude(lon: Optional[float]) -> bool:
    if lon is None:
        return False
    try:
        return LON_MIN <= float(lon) <= LON_MAX
    except (TypeError, ValueError):
        return False


def is_valid_zero_zero(lat: Optional[float], lon: Optional[float]) -> bool:
    """Explicitly reject (0, 0) as a real coordinate unless configured otherwise."""
    if lat == 0.0 and lon == 0.0:
        return False
    return True


def has_coordinates(lat: Optional[float], lon: Optional[float]) -> bool:
    return (
        is_valid_latitude(lat)
        and is_valid_longitude(lon)
        and is_valid_zero_zero(lat, lon)
    )


def validate_coordinates(lat: Optional[float], lon: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """Return (lat, lon) only when both are valid; otherwise (None, None).

    Rejects (0, 0) unless explicitly allowed, because many systems emit 0,0 for
    unknown GPS. The Context Agent should never treat (0,0) as a real location.
    """
    if not has_coordinates(lat, lon):
        return None, None
    return float(lat), float(lon)


def require_coordinates(lat: Optional[float], lon: Optional[float], field: str = "coordinates") -> Tuple[float, float]:
    """Like validate_coordinates but raises ValidationError when invalid."""
    lat_v, lon_v = validate_coordinates(lat, lon)
    if lat_v is None or lon_v is None:
        raise ValidationError(field, "invalid or missing coordinates", {"latitude": lat, "longitude": lon})
    return lat_v, lon_v
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\utils\validation.py'
encoded = base64.b64encode(content.encode("utf-8"))
decoded = base64.b64decode(encoded)
with open(target, "wb") as f:
    f.write(decoded)
print("written", len(decoded), "bytes")