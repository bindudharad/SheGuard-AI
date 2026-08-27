from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

# Enums
class ThreatLevel(str, Enum):
    SAFE = 'SAFE'
    WARNING = 'WARNING'
    HIGH = 'HIGH'
    CRITICAL = 'CRITICAL'
    EMERGENCY = 'EMERGENCY'

class ThreatType(str, Enum):
    NONE = 'none'
    POSSIBLE_CONFRONTATION = 'possible_confrontation'
    POSSIBLE_PHYSICAL_AGGRESSION = 'possible_physical_aggression'
    POSSIBLE_FALL = 'possible_fall'
    POSSIBLE_DISTRESS = 'possible_distress'
    ABNORMAL_MOVEMENT = 'abnormal_movement'
    DISTRESS_KEYWORD = 'distress_keyword'
    UNKNOWN = 'unknown'

class RiskFactor(str, Enum):
    VISION = 'vision'
    AUDIO = 'audio'
    CONTEXT = 'context'

# Input schemas
class VisionSignal(BaseModel):
    agent: str = 'vision_agent'
    timestamp: str
    persons_detected: int = 0
    interaction_detected: bool = False
    interaction_confidence: float = 0.0
    activity_label: Optional[str] = None
    activity_confidence: float = 0.0
    temporal_confidence: float = 0.0
    visual_risk_signal: float = 0.0
    evidence: List[str] = Field(default_factory=list)
    simulation: bool = False

class AudioSignal(BaseModel):
    agent: str = 'audio_agent'
    timestamp: str
    speech_detected: bool = False
    transcription_text: Optional[str] = None
    keywords: List[Dict[str, Any]] = Field(default_factory=list)
    distress_detected: bool = False
    distress_type: Optional[str] = None
    distress_confidence: float = 0.0
    simulation: bool = False

class ContextSignal(BaseModel):
    agent: str = 'context_agent'
    timestamp: str
    context_score: float = 0.0
    context_confidence: float = 0.0
    data_quality: float = 0.0
    time_period: Optional[str] = None
    isolation_status: Optional[str] = None
    nearby_incidents: int = 0
    security_distance_meters: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    simulation: bool = False

class ThreatRequest(BaseModel):
    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    vision: Optional[VisionSignal] = None
    audio: Optional[AudioSignal] = None
    context: Optional[ContextSignal] = None
    intelligence: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    simulation: bool = False

# Output schemas
class RiskContribution(BaseModel):
    factor: RiskFactor
    raw_score: float
    weight: float
    weighted_score: float
    confidence: float
    evidence: List[str] = Field(default_factory=list)

class ThreatResult(BaseModel):
    agent: str = 'threat_agent'
    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    risk_score: float = 0.0
    threat_level: ThreatLevel = ThreatLevel.SAFE
    threat_type: ThreatType = ThreatType.NONE
    confidence: float = 0.0
    
    contributions: List[RiskContribution] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    
    vision_available: bool = False
    audio_available: bool = False
    context_available: bool = False
    
    simulation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        d = self.dict()
        d['timestamp'] = self.timestamp.isoformat()
        d['threat_level'] = self.threat_level.value
        d['threat_type'] = self.threat_type.value
        return d

# Configurable weights
class ThreatWeights(BaseModel):
    vision_weight: float = 0.50
    audio_weight: float = 0.25
    context_weight: float = 0.25
    
    # Sub-weights within vision
    vision_interaction_weight: float = 0.40
    vision_activity_weight: float = 0.40
    vision_temporal_weight: float = 0.20
    
    # Sub-weights within audio
    audio_keyword_weight: float = 0.60
    audio_distress_weight: float = 0.40
    
    # Thresholds
    safe_max: float = 29.0
    warning_max: float = 59.0
    high_max: float = 79.0
    critical_min: float = 80.0
