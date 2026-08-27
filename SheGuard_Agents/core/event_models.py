"""
Standard Event Models for SheGuard Agents

Defines the canonical event contract used across all components.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from uuid import uuid4


class EventType(str, Enum):
    """Standardized event types across the SheGuard ecosystem"""
    # App -> Backend
    SOS_TRIGGERED = "SOS_TRIGGERED"
    HELP_TRIGGERED = "HELP_TRIGGERED"
    HELP_CANCELLED = "HELP_CANCELLED"
    
    # Backend -> Agents
    EMERGENCY_CREATED = "EMERGENCY_CREATED"
    TRACKING_STARTED = "TRACKING_STARTED"
    TRACKING_UPDATED = "TRACKING_UPDATED"
    TRACKING_STOPPED = "TRACKING_STOPPED"
    LOCATION_UPDATED = "LOCATION_UPDATED"
    
    # AI/CCTV -> Agents
    AI_ALERT = "AI_ALERT"
    CCTV_ALERT = "CCTV_ALERT"
    THREAT_DETECTED = "THREAT_DETECTED"
    NEARBY_CCTV_FOUND = "NEARBY_CCTV_FOUND"
    
    # Agents -> Backend
    POLICE_ALERT = "POLICE_ALERT"
    INCIDENT_ACKNOWLEDGED = "INCIDENT_ACKNOWLEDGED"
    INCIDENT_ASSIGNED = "INCIDENT_ASSIGNED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    
    # System
    NETWORK_OFFLINE = "NETWORK_OFFLINE"
    NETWORK_RECOVERED = "NETWORK_RECOVERED"
    EMERGENCY_TIMEOUT = "EMERGENCY_TIMEOUT"
    TRACKING_STALE = "TRACKING_STALE"


class ThreatLevel(str, Enum):
    """Threat prioritization levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EmergencyState(str, Enum):
    """Emergency session state machine"""
    IDLE = "IDLE"
    HELP_PENDING = "HELP_PENDING"
    EMERGENCY_CREATED = "EMERGENCY_CREATED"
    TRACKING_STARTING = "TRACKING_STARTING"
    TRACKING_ACTIVE = "TRACKING_ACTIVE"
    AI_ANALYSIS = "AI_ANALYSIS"
    CCTV_SEARCH = "CCTV_SEARCH"
    POLICE_ALERTED = "POLICE_ALERTED"
    POLICE_RESPONDING = "POLICE_RESPONDING"
    EMERGENCY_RESOLVED = "EMERGENCY_RESOLVED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"
    RECOVERING = "RECOVERING"


class BaseEvent(BaseModel):
    """Base event contract - all events must contain these fields"""
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    user_id: int
    session_id: str
    incident_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy: Optional[float] = None
    source: str = "agents"
    severity: Optional[str] = None
    confidence: float = 1.0
    status: str = "active"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SOSEvent(BaseEvent):
    """SOS emergency trigger"""
    event_type: EventType = EventType.SOS_TRIGGERED
    trigger_source: str = "manual"  # manual, auto_fall, auto_attack
    is_silent: bool = False


class HelpEvent(BaseEvent):
    """HELP trigger with cancellation window"""
    event_type: EventType = EventType.HELP_TRIGGERED
    help_timeout_seconds: int = 5


class LocationUpdateEvent(BaseEvent):
    """GPS location update"""
    event_type: EventType = EventType.LOCATION_UPDATED
    speed: Optional[float] = None
    battery: Optional[int] = None


class AIAlertEvent(BaseEvent):
    """AI detection result"""
    event_type: EventType = EventType.AI_ALERT
    ai_result: str  # NORMAL, SUSPICIOUS, THREAT, FALL, VIOLENCE, DISTRESS, UNKNOWN
    confidence: float
    camera_id: str
    detection_details: Dict[str, Any] = Field(default_factory=dict)


class CCTVAlertEvent(BaseEvent):
    """CCTV camera association"""
    event_type: EventType = EventType.NEARBY_CCTV_FOUND
    camera_id: str
    distance_meters: float
    camera_status: str  # ONLINE, OFFLINE
    rtsp_url: Optional[str] = None


class ThreatDetectedEvent(BaseEvent):
    """Threat prioritization result"""
    event_type: EventType = EventType.THREAT_DETECTED
    threat_level: ThreatLevel
    threat_score: float
    factors: Dict[str, float] = Field(default_factory=dict)


class EmergencyCreatedEvent(BaseEvent):
    """Emergency session created"""
    event_type: EventType = EventType.EMERGENCY_CREATED
    emergency_state: EmergencyState = EmergencyState.EMERGENCY_CREATED
    trigger_type: str  # SOS, HELP


class TrackingStartedEvent(BaseEvent):
    """Tracking session started"""
    event_type: EventType = EventType.TRACKING_STARTED
    tracking_url: Optional[str] = None


class PoliceAlertEvent(BaseEvent):
    """Police notification"""
    event_type: EventType = EventType.POLICE_ALERT
    threat_level: ThreatLevel
    priority: int = 1
    assigned_officer: Optional[str] = None


class IncidentResolvedEvent(BaseEvent):
    """Emergency resolved"""
    event_type: EventType = EventType.INCIDENT_RESOLVED
    resolution: str  # police_resolved, cancelled, false_alarm


# Union type for event handling
AnyEvent = SOSEvent | HelpEvent | LocationUpdateEvent | AIAlertEvent | CCTVAlertEvent | ThreatDetectedEvent | EmergencyCreatedEvent | TrackingStartedEvent | PoliceAlertEvent | IncidentResolvedEvent


def create_event(event_type: EventType, user_id: int, session_id: str, **kwargs) -> BaseEvent:
    """Factory function to create events"""
    event_map = {
        EventType.SOS_TRIGGERED: SOSEvent,
        EventType.HELP_TRIGGERED: HelpEvent,
        EventType.LOCATION_UPDATED: LocationUpdateEvent,
        EventType.AI_ALERT: AIAlertEvent,
        EventType.NEARBY_CCTV_FOUND: CCTVAlertEvent,
        EventType.THREAT_DETECTED: ThreatDetectedEvent,
        EventType.EMERGENCY_CREATED: EmergencyCreatedEvent,
        EventType.TRACKING_STARTED: TrackingStartedEvent,
        EventType.POLICE_ALERT: PoliceAlertEvent,
        EventType.INCIDENT_RESOLVED: IncidentResolvedEvent,
    }
    cls = event_map.get(event_type, BaseEvent)
    return cls(
        event_type=event_type,
        user_id=user_id,
        session_id=session_id,
        **kwargs
    )


# Idempotency tracking
class EventIdempotencyKey(BaseModel):
    """Key for deduplication"""
    event_id: str
    user_id: int
    session_id: str
    incident_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

