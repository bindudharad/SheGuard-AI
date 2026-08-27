from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DecisionAction(str, Enum):
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    INCREASE_MONITORING = "INCREASE_MONITORING"
    REQUEST_ADDITIONAL_INTELLIGENCE = "REQUEST_ADDITIONAL_INTELLIGENCE"
    CREATE_INCIDENT = "CREATE_INCIDENT"
    ESCALATE = "ESCALATE"
    EMERGENCY_RESPONSE = "EMERGENCY_RESPONSE"


@dataclass
class DecisionEvaluation:
    """Internal decision evaluation with reasoning and metadata."""
    action: DecisionAction
    reasoning: str
    confidence: float
    required_action: str
    next_agent: Optional[str] = None
    uncertainty: float = 0.0


class DecisionRequest(BaseModel):
    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    risk_score: float = 0.0
    threat_level: str = "SAFE"
    threat_type: str = "none"
    confidence: float = 0.0
    vision_available: bool = False
    audio_available: bool = False
    context_available: bool = False
    uncertainty: float = 0.0
    previous_decisions: int = 0
    timestamp: Optional[datetime] = None


class DecisionResult(BaseModel):
    agent: str = "decision_agent"
    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    decision: DecisionAction
    reasoning: str
    confidence: float
    required_action: str
    next_agent: Optional[str] = None
    uncertainty: float
    
    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["timestamp"] = self.timestamp.isoformat()
        d["decision"] = self.decision.value
        return d
