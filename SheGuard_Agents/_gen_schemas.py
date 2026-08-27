import base64, os

content = r'''
"""Pydantic schemas for the SheGuard Context Agent.

These schemas describe the *contextual evidence* produced by the Context Agent.
The agent deliberately does NOT decide whether a person is dangerous or declare an
emergency; it only produces structured context that the Threat Agent consumes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class TimePeriod(str, Enum):
    """Day/night classification of the event time (contextual only)."""

    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"
    LATE_NIGHT = "late_night"
    UNKNOWN = "unknown"


class LocationStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    FALLBACK = "FALLBACK"
    UNKNOWN = "UNKNOWN"


class IsolationStatus(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class DataStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class EnvironmentStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUESTED = "NOT_REQUESTED"


class SimulationScenario(str, Enum):
    NORMAL_CAMPUS = "NORMAL_CAMPUS"
    LATE_NIGHT = "LATE_NIGHT"
    ISOLATED_AREA = "ISOLATED_AREA"
    RECENT_INCIDENTS = "RECENT_INCIDENTS"
    HIGH_CONTEXT = "HIGH_CONTEXT"
    MISSING_GPS = "MISSING_GPS"
    DATABASE_OFFLINE = "DATABASE_OFFLINE"


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------
class ContextRequest(BaseModel):
    """Input to the Context Agent.

    Most fields are optional because the agent must degrade gracefully when the
    upstream system (Vision Agent, mobile app, database) does not provide them.
    """

    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    camera_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_source: Optional[str] = None
    location_timestamp: Optional[datetime] = None
    person_count: Optional[int] = None
    tracked_people: Optional[int] = None
    interaction_participants: Optional[int] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    zone_id: Optional[str] = None
    environment: Optional[dict] = None
    timestamp: Optional[datetime] = None
    simulation: bool = False
    simulation_scenario: Optional[SimulationScenario] = None


class LocationInput(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Output sub-schemas
# ---------------------------------------------------------------------------
class LocationContext(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    source: Optional[str] = None
    confidence: float = 0.0
    status: LocationStatus = LocationStatus.UNKNOWN
    zone_id: Optional[str] = None
    zone_name: Optional[str] = None


class CameraContext(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    zone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    online_status: Optional[str] = None


class TimeContext(BaseModel):
    local: str = ""
    period: TimePeriod = TimePeriod.UNKNOWN
    day_of_week: Optional[str] = None
    is_weekend: Optional[bool] = None
    hour: Optional[int] = None
    timezone: str = "UTC"


class PeopleContext(BaseModel):
    count: int = 0
    tracked: Optional[int] = None
    interaction_participants: Optional[int] = None


class HistoryContext(BaseModel):
    available: bool = True
    status: DataStatus = DataStatus.AVAILABLE
    nearby_incidents: int = 0
    recent_incidents: int = 0
    lookback_hours: int = 24
    radius_meters: int = 500
    weighted_history_score: float = 0.0
    notes: List[str] = Field(default_factory=list)


class IsolationContext(BaseModel):
    status: IsolationStatus = IsolationStatus.UNKNOWN
    score: float = 0.0
    reasons: List[str] = Field(default_factory=list)


class SecurityContext(BaseModel):
    nearest_security_distance_meters: Optional[float] = None
    nearest_security_name: Optional[str] = None
    nearby_cameras: List[str] = Field(default_factory=list)


class EnvironmentContext(BaseModel):
    status: EnvironmentStatus = EnvironmentStatus.UNAVAILABLE
    data: Optional[dict] = None


class ContextFactor(BaseModel):
    name: str
    weight: float
    value: float
    contribution: float
    available: bool = True
    note: Optional[str] = None


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------
class ContextResult(BaseModel):
    """Stable output schema for the Context Agent."""

    agent: str = "context_agent"
    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    location: LocationContext = Field(default_factory=LocationContext)
    camera: CameraContext = Field(default_factory=CameraContext)
    time: TimeContext = Field(default_factory=TimeContext)
    people: PeopleContext = Field(default_factory=PeopleContext)
    history: HistoryContext = Field(default_factory=HistoryContext)
    isolation: IsolationContext = Field(default_factory=IsolationContext)
    security: SecurityContext = Field(default_factory=SecurityContext)
    environment: EnvironmentContext = Field(default_factory=EnvironmentContext)

    context_score: float = 0.0
    context_confidence: float = 0.0
    data_quality: float = 0.0

    factors: List[ContextFactor] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)

    degraded: bool = False
    simulation: bool = False
    scenario: Optional[str] = None

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
class ZoneConfig(BaseModel):
    zone_id: str
    name: str
    zone_type: str = "general"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_meters: Optional[float] = None
    baseline_context: float = 0.0
    historical_activity_level: float = 0.0
    security_context: float = 0.0
    expected_occupancy: Optional[float] = None
    camera_ids: List[str] = Field(default_factory=list)
    security_resources: List[str] = Field(default_factory=list)


class SecurityResource(BaseModel):
    name: str
    latitude: float
    longitude: float
    kind: str = "security_post"


class ContextWeights(BaseModel):
    time: float = 0.15
    location: float = 0.20
    historical: float = 0.25
    proximity: float = 0.20
    isolation: float = 0.15
    environment: float = 0.05


class ContextConfig(BaseModel):
    enabled: bool = True
    timezone: str = "Asia/Kolkata"

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

    weights: ContextWeights = Field(default_factory=ContextWeights)

    zones: List[ZoneConfig] = Field(default_factory=list)
    security_resources: List[SecurityResource] = Field(default_factory=list)

    default_timezone: str = "Asia/Kolkata"

    def total_weight(self) -> float:
        w = self.weights
        return w.time + w.location + w.historical + w.proximity + w.isolation + w.environment
'''

target = r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\schemas.py'
encoded = base64.b64encode(content.encode('utf-8'))
with open(r'C:\Programs\codex\SheGuard\SheGuard_agents\agents\context\schemas_b64.txt', 'wb') as f:
    f.write(encoded)
decoded = base64.b64decode(encoded)
with open(target, 'wb') as f:
    f.write(decoded)
print('written', len(decoded), 'bytes')