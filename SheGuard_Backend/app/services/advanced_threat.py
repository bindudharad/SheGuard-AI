from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ThreatAssessment:
    score: int
    level: str
    reasons: list[str] = field(default_factory=list)
    kidnap_suspicion_score: int = 0


def assess_threat(
    incident_type: str,
    confidence: float,
    *,
    inactivity_duration: float = 0.0,
    motion_anomaly: float = 0.0,
    repeated_aggression: int = 0,
    sudden_acceleration: float = 0.0,
    tracking_instability: float = 0.0,
    created_at: datetime | None = None,
    extra_signals: dict[str, Any] | None = None,
) -> ThreatAssessment:
    event = incident_type.lower()
    score = 0.0
    reasons: list[str] = []

    if event == "fall":
        score += 3.5
        reasons.append("fall posture or collapse signal")
    if event in {"fight", "attack"}:
        score += 5.5
        reasons.append("aggressive interaction signal")
    if event in {"unconscious", "inactivity"}:
        score += 3.0
        reasons.append("prolonged inactivity signal")
    if confidence >= 0.90:
        score += 2.0
        reasons.append("very high AI confidence")
    elif confidence >= 0.75:
        score += 1.0
        reasons.append("sustained AI confidence")
    if inactivity_duration >= 20:
        score += 1.5
        reasons.append("extended absence of body movement")
    elif inactivity_duration >= 8:
        score += 0.8
        reasons.append("short-term stillness detected")
    if motion_anomaly >= 0.7:
        score += 1.3
        reasons.append("motion anomaly")
    if repeated_aggression >= 2:
        score += min(2.0, repeated_aggression * 0.6)
        reasons.append("repeated aggression pattern")
    if sudden_acceleration >= 0.7:
        score += 1.0
        reasons.append("sudden acceleration")
    if tracking_instability >= 0.7:
        score += 0.7
        reasons.append("tracking instability during event")

    when = created_at or datetime.now()
    if when.hour >= 20 or when.hour < 5:
        score += 1.0
        reasons.append("nighttime weighting")

    extra_signals = extra_signals or {}
    dragging = float(extra_signals.get("dragging_score", 0.0) or 0.0)
    resistance = float(extra_signals.get("resistance_score", 0.0) or 0.0)
    route_changes = float(extra_signals.get("route_change_score", 0.0) or 0.0)
    kidnap_suspicion = int(round(min(10.0, dragging * 4 + resistance * 3 + route_changes * 2 + repeated_aggression * 0.7)))
    if kidnap_suspicion >= 5:
        reasons.append("suspicious forced movement indicators")
        score += min(1.5, kidnap_suspicion / 10)

    final_score = int(round(max(0.0, min(score, 10.0))))
    return ThreatAssessment(final_score, threat_level(final_score), reasons or ["baseline safety signal"], kidnap_suspicion)


def threat_level(score: int) -> str:
    if score >= 9:
        return "CRITICAL"
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def explain_detection(event_type: str, assessment: ThreatAssessment) -> str:
    bullets = "\n".join(f"- {reason}" for reason in assessment.reasons)
    return f"{event_type.title()} detected because:\n{bullets}\nThreat Score: {assessment.score}/10 ({assessment.level})"

