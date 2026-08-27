import base64, os

content = r'''
"""Proximity analysis: nearby incidents, security resources, cameras."""

from __future__ import annotations

from typing import Optional

from agents.context.schemas import SecurityContext, SecurityResource
from agents.context.utils.geo import haversine_distance_meters, nearest_distance


class ProximityAnalyzer:
    """Finds distances to security resources, cameras, and other reference points."""

    def __init__(self, security_resources: list[SecurityResource] | None = None, nearby_cameras: list[tuple[str, float, float]] | None = None):
        self.security_resources = security_resources or []
        self.nearby_cameras = nearby_cameras or []  # (camera_id, lat, lon)

    def analyze(
        self,
        lat: float,
        lon: float,
    ) -> SecurityContext:
        if lat is None or lon is None:
            return SecurityContext()

        # Nearest security
        sec_points = [(r.latitude, r.longitude) for r in self.security_resources]
        dist = nearest_distance(lat, lon, sec_points)
        nearest_name = None
        if dist is not None and self.security_resources:
            idx = min(range(len(self.security_resources)), key=lambda i: haversine_distance_meters(lat, lon, self.security_resources[i].latitude, self.security_resources[i].longitude))
            nearest_name = self.security_resources[idx].name

        # Nearby cameras
        cam_ids = []
        for cam_id, c_lat, c_lon in self.nearby_cameras:
            if c_lat is not None and c_lon is not None:
                d = haversine_distance_meters(lat, lon, c_lat, c_lon)
                if d <= 500:  # default radius
                    cam_ids.append(cam_id)

        return SecurityContext(
            nearest_security_distance_meters=dist,
            nearest_security_name=nearest_name,
            nearby_cameras=cam_ids,
        )

    def factor(self, context: SecurityContext) -> float:
        """Security proximity factor: closer = lower contextual risk (more help available).

        We invert the distance: closer security = lower context risk.
        """
        dist = context.nearest_security_distance_meters
        if dist is None:
            return 0.5  # neutral
        if dist <= 50:
            return 0.1
        elif dist <= 100:
            return 0.2
        elif dist <= 250:
            return 0.35
        elif dist <= 500:
            return 0.5
        elif dist <= 1000:
            return 0.65
        else:
            return 0.8
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\analyzers\proximity_analyzer.py'
encoded = base64.b64encode(content.encode("utf-8"))
decoded = base64.b64decode(encoded)
with open(target, "wb") as f:
    f.write(decoded)
print("written", len(decoded), "bytes")