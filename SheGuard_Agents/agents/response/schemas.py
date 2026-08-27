from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

class IncidentStatus(str, Enum):
    ACTIVE = 'ACTIVE'
    ESCALATED = 'ESCALATED'
    RESOLVED = 'RESOLVED'
    FALSE_POSITIVE = 'FALSE_POSITIVE'

class NotificationChannel(str, Enum):
    TELEGRAM = 'TELEGRAM'
    SMS = 'SMS'
    EMAIL = 'EMAIL'
    MOBILE_PUSH = 'MOBILE_PUSH'
    DASHBOARD = 'DASHBOARD'

class ResponseAction(str, Enum):
    CREATE_INCIDENT = 'CREATE_INCIDENT'
    NOTIFY_GUARDIAN = 'NOTIFY_GUARDIAN'
    SECURE_EVIDENCE = 'SECURE_EVIDENCE'
    GET_LOCATION = 'GET_LOCATION'
    UPDATE_DASHBOARD = 'UPDATE_DASHBOARD'
    EMERGENCY_DISPATCH = 'EMERGENCY_DISPATCH'

class ResponseRequest(BaseModel):
    incident_id: str
    trace_id: Optional[str] = None
    decision: str
    risk_score: float
    threat_level: str
    threat_type: str
    confidence: float
    vision_data: Optional[Dict[str, Any]] = None
    audio_data: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    intelligence_data: Optional[Dict[str, Any]] = None
    simulation: bool = False

class EvidenceRecord(BaseModel):
    evidence_id: str
    incident_id: str
    type: str  # 'video', 'image', 'audio'
    path: str
    sha256: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class NotificationRecord(BaseModel):
    notification_id: str
    incident_id: str
    channel: NotificationChannel
    recipient: str
    status: str  # 'sent', 'failed', 'pending'
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

class ResponseResult(BaseModel):
    agent: str = 'response_agent'
    incident_id: str
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    status: IncidentStatus = IncidentStatus.ACTIVE
    actions_taken: List[ResponseAction] = Field(default_factory=list)
    evidence: List[EvidenceRecord] = Field(default_factory=list)
    notifications: List[NotificationRecord] = Field(default_factory=list)
    location: Optional[Dict[str, Any]] = None
    
    simulation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        d = self.dict()
        d['timestamp'] = self.timestamp.isoformat()
        d['status'] = self.status.value
        d['actions_taken'] = [a.value for a in self.actions_taken]
        d['evidence'] = [e.dict() for e in self.evidence]
        d['notifications'] = [n.dict() for n in self.notifications]
        return d
