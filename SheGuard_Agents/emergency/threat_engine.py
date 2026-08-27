"""Operational threat prioritization for SheGuard emergencies.

This is an operational triage score (LOW/MEDIUM/HIGH/CRITICAL) - NOT a
medically or legally validated risk score. Inputs are weighted additively and
capped at 100.
"""
from __future__ import annotations

from typing import Optional

from core.event_models import ThreatLevel
from emergency.models import SessionContext, ThreatAssessment

# Level thresholds on the 0-100 scale.
CRITICAL_AT = 85.0
HIGH_AT = 62.0
MEDIUM_AT = 38.0

# Base scores per trigger.
BASE_SOS = 70.0
BASE_SILENT_SOS = 74.0
BASE_HELP_CONFIRMED = 55.0

# AI result bonuses (added once AI evidence exists).
AI_BONUS = {
    "VIOLENCE": 18.0,
    "THREAT": 16.0,
    "FALL": 12.0,
    "DISTRESS": 10.0,
    "SUSPICIOUS": 6.0,
}

CONFIDENCE_SCALE = 12.0  # ai_confidence 0..1 -> up to +12
CCTV_CORROBORATION = 8.0
ONLINE_CAMERA_CLOSE = 4.0  # closest camera < 150m and online
TRACKING_ACTIVE = 5.0
NO_LOCATION_UNCERTAINTY = 8.0
REPEATED_ALERT = 6.0  # per repeat, capped at 2
DURATION_ESCALATION_AFTER = 300.0  # seconds
DURATION_ESCALATION = 8.0


def evaluate(ctx: SessionContext) -> ThreatAssessment:
    factors: dict[str, float] = {}
    reasons: list[str] = []

    if ctx.trigger == "HELP":
        base = BASE_HELP_CONFIRMED
        reasons.append("HELP confirmed emergency")
    elif ctx.silent:
        base = BASE_SILENT_SOS
        reasons.append("Silent SOS triggered")
    else:
        base = BASE_SOS
        reasons.append("SOS triggered")
    factors["trigger"] = base

    if ctx.ai_result:
        bonus = AI_BONUS.get(ctx.ai_result, 4.0)
        factors["ai_detection"] = bonus
        reasons.append(f"AI detected {ctx.ai_result}")
        confidence = ctx.ai_confidence if ctx.ai_confidence is not None else 0.7
        conf_pts = CONFIDENCE_SCALE * max(0.0, min(1.0, confidence))
        if conf_pts > 0:
            factors["ai_confidence"] = conf_pts

    online_cameras = [c for c in ctx.cameras if c.online_status.lower() == "online"]
    if ctx.cameras:
        factors["cctv_corroboration"] = CCTV_CORROBORATION
        reasons.append(f"{len(ctx.cameras)} nearby CCTV associated")
        if online_cameras:
            closest = min(
                (c.distance_meters for c in online_cameras if c.distance_meters is not None),
                default=None,
            )
            if closest is not None and closest <= 150:
                factors["cctv_close"] = ONLINE_CAMERA_CLOSE

    if ctx.tracking_active:
        factors["tracking_active"] = TRACKING_ACTIVE

    if ctx.latitude is None or ctx.longitude is None:
        factors["no_location"] = NO_LOCATION_UNCERTAINTY
        reasons.append("No GPS fix - uncertainty penalty")

    if ctx.repeated_alerts > 0:
        pts = REPEATED_ALERT * min(ctx.repeated_alerts, 2)
        factors["repeated_alerts"] = pts
        reasons.append(f"{ctx.repeated_alerts} repeated alert(s)")

    duration = ctx.duration_seconds()
    if duration >= DURATION_ESCALATION_AFTER:
        factors["duration"] = DURATION_ESCALATION
        reasons.append(f"Emergency active for {int(duration)}s")

    score = min(100.0, sum(factors.values()))

    if score >= CRITICAL_AT:
        level = ThreatLevel.CRITICAL
    elif score >= HIGH_AT:
        level = ThreatLevel.HIGH
    elif score >= MEDIUM_AT:
        level = ThreatLevel.MEDIUM
    else:
        level = ThreatLevel.LOW

    return ThreatAssessment(threat_level=level, score=score, factors=factors, reasons=reasons)
