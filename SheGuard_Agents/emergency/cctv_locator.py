"""Nearby CCTV association for emergencies.

Given victim coordinates and the backend camera registry, pick the closest
useful cameras. Cameras without coordinates cannot be geo-matched and are only
reported as "unknown distance" when nothing better exists - we never claim
physical coverage that metadata does not support.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Optional

from emergency.models import CameraAssociation

EARTH_RADIUS_M = 6_371_000.0


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def associate_cameras(
    cameras: Iterable[dict],
    latitude: Optional[float],
    longitude: Optional[float],
    max_distance_meters: float = 500.0,
    max_cameras: int = 3,
) -> List[CameraAssociation]:
    """Return up to `max_cameras` cameras ordered by usefulness.

    Online + geo-matchable cameras come first (closest). If no camera has
    coordinates, online cameras are still returned (distance unknown) so the
    orchestrator can request analysis from the live local stream.
    """
    parsed: List[CameraAssociation] = []
    for cam in cameras or []:
        try:
            assoc = CameraAssociation(
                camera_id=int(cam.get("camera_id")),
                camera_name=str(cam.get("camera_name") or f"Camera {cam.get('camera_id')}"),
                distance_meters=None,
                online_status=str(cam.get("online_status") or "unknown"),
                rtsp_url=cam.get("rtsp_url"),
                latitude=cam.get("latitude"),
                longitude=cam.get("longitude"),
            )
        except (TypeError, ValueError):
            continue
        if latitude is not None and longitude is not None and assoc.latitude is not None and assoc.longitude is not None:
            assoc.distance_meters = haversine_meters(latitude, longitude, float(assoc.latitude), float(assoc.longitude))
        parsed.append(assoc)

    online_geo = [
        c
        for c in parsed
        if c.online_status.lower() == "online" and c.distance_meters is not None and c.distance_meters <= max_distance_meters
    ]
    online_geo.sort(key=lambda c: c.distance_meters)

    online_unknown = [c for c in parsed if c.online_status.lower() == "online" and c.distance_meters is None]

    selected = online_geo[:max_cameras]
    remaining = max_cameras - len(selected)
    if remaining > 0:
        selected.extend(online_unknown[:remaining])

    # Fall back to cameras without coordinates (e.g. the live local DroidCam)
    # only if there is literally nothing else - their distance is unknown, so
    # we never claim physical coverage.
    if not selected:
        unknown_location = [c for c in parsed if c.distance_meters is None]
        selected = unknown_location[:1]

    return selected


def best_camera(cameras: List[CameraAssociation]) -> Optional[CameraAssociation]:
    """The closest ONLINE camera usable for AI analysis, if any."""
    online = [c for c in cameras if c.online_status.lower() == "online"]
    if not online:
        return None
    with_distance = [c for c in online if c.distance_meters is not None]
    if with_distance:
        return min(with_distance, key=lambda c: c.distance_meters)
    return online[0]
