"""Runtime models for the emergency orchestrator.

Reuses the canonical event contract from core.event_models (EventType,
EmergencyState, ThreatLevel) so agents speak exactly the same language as the
rest of SheGuard. Adds per-session runtime context - never a global singleton.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.event_models import EmergencyState, EventType, ThreatLevel


@dataclass
class StandardEvent:
    """Normalized event consumed/produced by the orchestrator."""

    event_type: EventType
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    incident_id: Optional[int] = None
    event_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    speed: Optional[float] = None
    battery: Optional[int] = None
    source: str = "backend"
    severity: Optional[str] = None
    confidence: float = 1.0
    camera_id: Optional[str] = None
    incident_type: Optional[str] = None
    ai_result: Optional[str] = None
    status: Optional[str] = None
    silent: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        return self.event_id or f"{self.event_type.value}:{self.user_id}:{self.incident_id}:{self.session_id}"


# Incident types produced by the mobile app (SOS path).
SOS_INCIDENT_TYPES = {"manual_sos", "silent_sos", "sos", "help"}

# Incident types produced by SheGuard_AI CCTV analysis.
AI_THREAT_TYPES = {
    "fall": "FALL",
    "attack": "VIOLENCE",
    "fight": "VIOLENCE",
    "violence": "VIOLENCE",
    "distress": "DISTRESS",
    "weapon": "THREAT",
    "intrusion": "SUSPICIOUS",
}

APP_EVENT_SOURCE_PREFIXES = ("manual_sos", "silent_sos")


def is_sos_incident(incident_type: str | None) -> bool:
    return (incident_type or "").lower() in SOS_INCIDENT_TYPES


def map_ai_incident(incident_type: str | None) -> Optional[str]:
    """Map an AI incident type onto the orchestrator's AI result vocabulary."""
    return AI_THREAT_TYPES.get((incident_type or "").lower())


@dataclass
class CameraAssociation:
    camera_id: int
    camera_name: str
    distance_meters: Optional[float]
    online_status: str
    rtsp_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "camera_name": self.camera_name,
            "distance_meters": round(self.distance_meters, 1) if self.distance_meters is not None else None,
            "online_status": self.online_status,
            "rtsp_url": self.rtsp_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "usable_for_analysis": self.online_status.lower() == "online" and self.rtsp_url is not None
            or self.online_status.lower() == "online",
        }


@dataclass
class ThreatAssessment:
    threat_level: ThreatLevel
    score: float
    factors: Dict[str, float] = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "threat_level": self.threat_level.value,
            "score": round(self.score, 1),
            "factors": {k: round(v, 1) for k, v in self.factors.items()},
            "reasons": self.reasons,
        }


@dataclass
class SessionContext:
    """Isolated state for ONE user's ONE emergency session.

    Multiple SessionContexts may be active simultaneously; nothing here is
    shared between users.
    """

    session_id: str
    user_id: int
    state: EmergencyState = EmergencyState.IDLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    trigger: str = "SOS"  # SOS | HELP
    trigger_source: str = "manual"
    silent: bool = False

    incident_ids: List[int] = field(default_factory=list)
    backend_session_created: bool = False

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    last_location_at: Optional[datetime] = None

    tracking_active: bool = False
    stale_notified: bool = False

    cameras: List[CameraAssociation] = field(default_factory=list)
    ai_requested: bool = False
    ai_result: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_unavailable: bool = False

    threat: Optional[ThreatAssessment] = None
    police_alerted: bool = False
    repeated_alerts: int = 0

    degraded: Dict[str, bool] = field(default_factory=dict)  # e.g. {"ai": True}
    help_timer_handle: Any = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None

    # ---- transitions -----------------------------------------------------
    ALLOWED: Dict[EmergencyState, set] = field(
        default_factory=lambda: {
            EmergencyState.IDLE: {
                EmergencyState.HELP_PENDING,
                EmergencyState.EMERGENCY_CREATED,
                EmergencyState.CANCELLED,
                EmergencyState.ERROR,
            },
            EmergencyState.HELP_PENDING: {
                EmergencyState.EMERGENCY_CREATED,
                EmergencyState.CANCELLED,
                EmergencyState.ERROR,
            },
            EmergencyState.EMERGENCY_CREATED: {
                EmergencyState.TRACKING_STARTING,
                EmergencyState.TRACKING_ACTIVE,
                EmergencyState.CCTV_SEARCH,
                EmergencyState.POLICE_ALERTED,
                EmergencyState.CANCELLED,
                EmergencyState.ERROR,
                EmergencyState.RECOVERING,
            },
            EmergencyState.TRACKING_STARTING: {
                EmergencyState.TRACKING_ACTIVE,
                EmergencyState.RECOVERING,
                EmergencyState.CANCELLED,
                EmergencyState.ERROR,
            },
            EmergencyState.TRACKING_ACTIVE: {
                EmergencyState.AI_ANALYSIS,
                EmergencyState.CCTV_SEARCH,
                EmergencyState.POLICE_ALERTED,
                EmergencyState.OFFLINE,
                EmergencyState.EMERGENCY_RESOLVED,
                EmergencyState.CANCELLED,
                EmergencyState.ERROR,
                EmergencyState.TRACKING_STARTING,
            },
            EmergencyState.AI_ANALYSIS: {
                EmergencyState.CCTV_SEARCH,
                EmergencyState.POLICE_ALERTED,
                EmergencyState.TRACKING_ACTIVE,
                EmergencyState.EMERGENCY_RESOLVED,
                EmergencyState.CANCELLED,
            },
            EmergencyState.CCTV_SEARCH: {
                EmergencyState.AI_ANALYSIS,
                EmergencyState.POLICE_ALERTED,
                EmergencyState.TRACKING_ACTIVE,
                EmergencyState.EMERGENCY_RESOLVED,
                EmergencyState.CANCELLED,
            },
            EmergencyState.POLICE_ALERTED: {
                EmergencyState.POLICE_RESPONDING,
                EmergencyState.EMERGENCY_RESOLVED,
                EmergencyState.CANCELLED,
                EmergencyState.AI_ANALYSIS,
                EmergencyState.CCTV_SEARCH,
                EmergencyState.OFFLINE,
            },
            EmergencyState.POLICE_RESPONDING: {
                EmergencyState.EMERGENCY_RESOLVED,
                EmergencyState.POLICE_ALERTED,
                EmergencyState.CANCELLED,
            },
            EmergencyState.EMERGENCY_RESOLVED: set(),
            EmergencyState.CANCELLED: set(),
            EmergencyState.ERROR: {
                EmergencyState.RECOVERING,
                EmergencyState.CANCELLED,
                EmergencyState.EMERGENCY_RESOLVED,
            },
            EmergencyState.OFFLINE: {EmergencyState.RECOVERING, EmergencyState.TRACKING_ACTIVE},
            EmergencyState.RECOVERING: {
                EmergencyState.TRACKING_ACTIVE,
                EmergencyState.POLICE_ALERTED,
                EmergencyState.ERROR,
                EmergencyState.EMERGENCY_RESOLVED,
            },
        }
    )

    def transition(self, new_state: EmergencyState, force: bool = False) -> bool:
        if new_state == self.state:
            return True
        allowed = self.ALLOWED.get(self.state, set())
        if not force and new_state not in allowed:
            return False
        self.state = new_state
        self.updated_at = datetime.utcnow()
        return True

    @property
    def is_terminal(self) -> bool:
        return self.state in (
            EmergencyState.EMERGENCY_RESOLVED,
            EmergencyState.CANCELLED,
        )

    @property
    def is_active(self) -> bool:
        return not self.is_terminal

    def duration_seconds(self) -> float:
        end = self.resolved_at or datetime.utcnow()
        return max(0.0, (end - self.created_at).total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "trigger": self.trigger,
            "trigger_source": self.trigger_source,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_seconds": round(self.duration_seconds(), 1),
            "incident_ids": list(self.incident_ids),
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "accuracy": self.accuracy,
                "last_location_at": self.last_location_at.isoformat() if self.last_location_at else None,
            },
            "tracking_active": self.tracking_active,
            "stale_flagged": self.stale_notified,
            "cameras": [c.to_dict() for c in self.cameras],
            "ai": {
                "requested": self.ai_requested,
                "result": self.ai_result,
                "confidence": self.ai_confidence,
                "unavailable": self.ai_unavailable,
            },
            "threat": self.threat.to_dict() if self.threat else None,
            "police_alerted": self.police_alerted,
            "repeated_alerts": self.repeated_alerts,
            "degraded": dict(self.degraded),
            "resolution": self.resolution,
        }
