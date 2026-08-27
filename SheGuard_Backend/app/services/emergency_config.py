from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EmergencyResponseConfig:
    incident_match_radius_meters: float = float(os.environ.get("SHEGUARD_INCIDENT_MATCH_RADIUS_METERS", "75"))
    active_location_max_age_seconds: int = int(os.environ.get("SHEGUARD_ACTIVE_LOCATION_MAX_AGE_SECONDS", "900"))
    incident_cooldown_seconds: int = int(os.environ.get("SHEGUARD_INCIDENT_COOLDOWN_SECONDS", "120"))
    notification_cooldown_seconds: int = int(os.environ.get("SHEGUARD_NOTIFICATION_COOLDOWN_SECONDS", "180"))
    notification_retry_count: int = int(os.environ.get("SHEGUARD_NOTIFICATION_RETRY_COUNT", "3"))
    evidence_retention_days: int = int(os.environ.get("SHEGUARD_EVIDENCE_RETENTION_DAYS", "30"))
    websocket_refresh_interval_seconds: int = int(os.environ.get("SHEGUARD_WEBSOCKET_REFRESH_INTERVAL_SECONDS", "5"))
    base_url: str = os.environ.get("SHEGUARD_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


settings = EmergencyResponseConfig()
