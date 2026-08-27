
"""Context Agent configuration using Pydantic Settings with CONTEXT_ prefix."""

from __future__ import annotations

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from agents.context.schemas import (
    ContextConfig,
    ContextWeights,
    ZoneConfig,
    SecurityResource,
)


class ContextSettings(BaseSettings):
    """Runtime configuration loaded from environment variables with CONTEXT_ prefix."""

    enabled: bool = True
    timezone: str = "Asia/Kolkata"
    default_timezone: str = "Asia/Kolkata"

    night_start: str = "22:00"
    night_end: str = "05:00"

    nearby_radius_meters: int = 500
    lookback_hours: int = 24
    max_history_records: int = 100

    history_decay_hours: float = 24.0
    history_decay_half_life: float = 12.0

    cache_camera_ttl_seconds: int = 300
    cache_history_ttl_seconds: int = 60
    cache_weather_ttl_seconds: int = 600
    cache_zone_ttl_seconds: int = 600

    location_stale_seconds: int = 600

    weights_time: float = 0.15
    weights_location: float = 0.20
    weights_historical: float = 0.25
    weights_proximity: float = 0.20
    weights_isolation: float = 0.15
    weights_environment: float = 0.05

    # Zone configs as JSON string for complex nested config
    zones_json: Optional[str] = None
    security_resources_json: Optional[str] = None

    model_config = SettingsConfigDict(
        env_prefix="CONTEXT_",
        env_file=(".env", ".env.example"),
        extra="ignore",
    )

    def to_context_config(self) -> ContextConfig:
        import json
        zones = []
        if self.zones_json:
            try:
                zones_data = json.loads(self.zones_json)
                zones = [ZoneConfig(**z) for z in zones_data]
            except Exception:
                zones = []
        security_resources = []
        if self.security_resources_json:
            try:
                res_data = json.loads(self.security_resources_json)
                security_resources = [SecurityResource(**r) for r in res_data]
            except Exception:
                security_resources = []

        return ContextConfig(
            enabled=self.enabled,
            timezone=self.timezone,
            default_timezone=self.default_timezone,
            night_start=self.night_start,
            night_end=self.night_end,
            nearby_radius_meters=self.nearby_radius_meters,
            lookback_hours=self.lookback_hours,
            max_history_records=self.max_history_records,
            history_decay_hours=self.history_decay_hours,
            history_decay_half_life=self.history_decay_half_life,
            cache_camera_ttl_seconds=self.cache_camera_ttl_seconds,
            cache_history_ttl_seconds=self.cache_history_ttl_seconds,
            cache_weather_ttl_seconds=self.cache_weather_ttl_seconds,
            cache_zone_ttl_seconds=self.cache_zone_ttl_seconds,
            location_stale_seconds=self.location_stale_seconds,
            weights=ContextWeights(
                time=self.weights_time,
                location=self.weights_location,
                historical=self.weights_historical,
                proximity=self.weights_proximity,
                isolation=self.weights_isolation,
                environment=self.weights_environment,
            ),
            zones=zones,
            security_resources=security_resources,
        )


def get_context_config() -> ContextConfig:
    return ContextSettings().to_context_config()
