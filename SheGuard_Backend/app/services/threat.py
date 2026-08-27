from datetime import datetime

from app.services.advanced_threat import assess_threat, threat_level


def calculate_threat_score(incident_type: str, confidence: float, speed: float | None = None, created_at: datetime | None = None) -> int:
    assessment = assess_threat(
        incident_type,
        confidence,
        motion_anomaly=1.0 if speed is not None and speed >= 3.5 else 0.0,
        created_at=created_at,
    )
    return assessment.score


def threat_label(score: int) -> str:
    return threat_level(score)
