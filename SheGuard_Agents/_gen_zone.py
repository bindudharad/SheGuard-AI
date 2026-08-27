import base64, os

content = r'''
"""Zone analysis: match location to zone, compute isolation factor from zone metadata."""

from __future__ import annotations

from typing import Optional

from agents.context.schemas import ZoneConfig, IsolationContext, IsolationStatus, LocationContext
from agents.context.utils.geo import haversine_distance_meters, point_in_circle


class ZoneAnalyzer:
    """Matches coordinates to a configured zone and computes isolation from metadata.

    Isolation is derived from zone metadata such as expected occupancy, security
    resources, camera density, and zone type. A zone without metadata defaults to
    UNKNOWN isolation.
    """

    def __init__(self, zones: list[ZoneConfig] | None = None):
        self.zones = zones or []

    def find_zone(self, lat: float, lon: float) -> Optional[ZoneConfig]:
        for zone in self.zones:
            if zone.latitude is not None and zone.longitude is not None and zone.radius_meters is not None:
                if point_in_circle(lat, lon, zone.latitude, zone.longitude, zone.radius_meters):
                    return zone
        return None

    def analyze(self, location: LocationContext) -> IsolationContext:
        if location.latitude is None or location.longitude is None:
            return IsolationContext(status=IsolationStatus.UNKNOWN, score=0.0, reasons=["no location"])

        zone = self.find_zone(location.latitude, location.longitude)
        if zone is None:
            return IsolationContext(
                status=IsolationStatus.UNKNOWN,
                score=0.0,
                reasons=["no matching zone"],
            )

        reasons = []
        score = 0.0

        # Base isolation from zone metadata
        if zone.zone_type in ("isolated", "parking", "perimeter", "boundary"):
            score += 0.4
            reasons.append(f"zone type: {zone.zone_type}")

        # Expected occupancy (low = more isolated)
        if zone.expected_occupancy is not None:
            if zone.expected_occupancy < 5:
                score += 0.25
                reasons.append("low expected occupancy")
            elif zone.expected_occupancy < 20:
                score += 0.1
                reasons.append("moderate expected occupancy")

        # Security context
        if zone.security_context > 0.5:
            score -= 0.15
            reasons.append("high security presence")

        # Camera count
        cam_count = len(zone.camera_ids)
        if cam_count == 0:
            score += 0.2
            reasons.append("no cameras in zone")
        elif cam_count < 3:
            score += 0.05
            reasons.append("limited camera coverage")

        # Historical activity level (high = more incidents historically)
        if zone.historical_activity_level > 0.7:
            score += 0.15
            reasons.append("elevated historical activity")

        score = max(0.0, min(1.0, score))

        if score >= 0.6:
            status = IsolationStatus.ELEVATED
        elif score >= 0.35:
            status = IsolationStatus.NORMAL
        elif score > 0:
            status = IsolationStatus.LOW
        else:
            status = IsolationStatus.UNKNOWN

        return IsolationContext(status=status, score=score, reasons=reasons)

    def factor(self, isolation: IsolationContext) -> float:
        """Isolation factor is the isolation score scaled to [0,1]."""
        return isolation.score
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\analyzers\zone_analyzer.py'
encoded = base64.b64encode(content.encode("utf-8"))
decoded = base64.b64decode(encoded)
with open(target, "wb") as f:
    f.write(decoded)
print("written", len(decoded), "bytes")