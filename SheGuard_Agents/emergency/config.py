"""Centralized configuration for the SheGuard emergency orchestrator.

All endpoints come from environment variables so no IP is hardcoded in logic:
    SHEGUARD_BACKEND_URL      (default http://192.168.1.3:8000)
    SHEGUARD_AI_URL           (optional, empty by default)
    SHEGUARD_DASHBOARD_URL    (informational)
    SHEGUARD_SERVICE_TOKEN    (shared AI-engine token accepted by the backend)
    SHEGUARD_AGENT_PHONE_NUMBER / SHEGUARD_AGENT_PASSWORD  (service login used
                              for user-scoped endpoints such as camera list)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass
class EmergencyConfig:
    # Endpoints
    backend_url: str = field(default_factory=lambda: _env("SHEGUARD_BACKEND_URL", "http://192.168.1.3:8000").rstrip("/"))
    ai_base_url: str = field(default_factory=lambda: _env("SHEGUARD_AI_URL", "").rstrip("/"))
    dashboard_url: str = field(default_factory=lambda: _env("SHEGUARD_DASHBOARD_URL", "http://127.0.0.1:5173").rstrip("/"))

    # Credentials - service token first (accepted on incidents/create and the
    # /agents/* sync routes), plus a normal service login for user-scoped reads.
    service_token: str = field(default_factory=lambda: _env("SHEGUARD_SERVICE_TOKEN", ""))
    agent_phone_number: str = field(default_factory=lambda: _env("SHEGUARD_AGENT_PHONE_NUMBER", "9298211739"))
    agent_password: str = field(default_factory=lambda: _env("SHEGUARD_AGENT_PASSWORD", "SheGuard@123"))

    # Orchestration tuning
    help_timeout_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_HELP_TIMEOUT_SECONDS", 5.0))
    tracking_stale_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_TRACKING_STALE_SECONDS", 60.0))
    stale_check_interval_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_STALE_CHECK_INTERVAL", 10.0))
    max_active_emergencies_per_user: int = field(default_factory=lambda: _env_int("SHEGUARD_MAX_ACTIVE_PER_USER", 1))
    duplicate_sos_window_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_DUPLICATE_WINDOW_SECONDS", 30.0))

    # CCTV association tuning
    max_cctv_distance_meters: float = field(default_factory=lambda: _env_float("SHEGUARD_MAX_CCTV_DISTANCE_METERS", 500.0))
    max_cameras_per_emergency: int = field(default_factory=lambda: _env_int("SHEGUARD_MAX_CCTV_CAMERAS", 3))

    # HTTP resilience
    request_timeout_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_HTTP_TIMEOUT_SECONDS", 8.0))
    max_retries: int = field(default_factory=lambda: _env_int("SHEGUARD_HTTP_MAX_RETRIES", 3))
    retry_base_delay_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_RETRY_BASE_DELAY", 0.5))
    circuit_breaker_threshold: int = field(default_factory=lambda: _env_int("SHEGUARD_BREAKER_THRESHOLD", 4))
    circuit_breaker_cooldown_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_BREAKER_COOLDOWN", 15.0))

    # WebSocket reconnect
    ws_reconnect_min_seconds: float = 1.0
    ws_reconnect_max_seconds: float = 15.0

    # Idempotency
    idempotency_ttl_seconds: float = field(default_factory=lambda: _env_float("SHEGUARD_IDEMPOTENCY_TTL", 3600.0))

    @property
    def ws_live_url(self) -> str:
        return self.backend_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws/live"

    @property
    def ai_available(self) -> bool:
        return bool(self.ai_base_url)


_config: EmergencyConfig | None = None


def get_emergency_config() -> EmergencyConfig:
    global _config
    if _config is None:
        _config = EmergencyConfig()
    return _config


def reset_emergency_config() -> None:
    global _config
    _config = None
