from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

class PaymentState(str, Enum):
    REQUESTED = 'REQUESTED'
    PAYMENT_REQUIRED = 'PAYMENT_REQUIRED'
    PAYMENT_SUBMITTED = 'PAYMENT_SUBMITTED'
    VERIFYING = 'VERIFYING'
    CONFIRMED = 'CONFIRMED'
    FAILED = 'FAILED'
    TIMEOUT = 'TIMEOUT'
    CANCELLED = 'CANCELLED'
    SIMULATED = 'SIMULATED'

class X402Request(BaseModel):
    incident_id: str
    trace_id: Optional[str] = None
    risk_score: float
    threat_level: str
    vision: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    simulation: bool = False

class X402Result(BaseModel):
    agent: str = 'x402_agent'
    incident_id: str
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    payment_id: str
    state: PaymentState
    service: str = 'safety-intelligence'
    amount: float = 0.01
    currency: str = 'ALGO'
    network: str = 'testnet'
    transaction_id: Optional[str] = None
    
    # Intelligence result
    risk_score: Optional[float] = None
    confidence: Optional[float] = None
    threat_type: Optional[str] = None
    reasons: list = Field(default_factory=list)
    
    simulation: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        d = self.dict()
        d['timestamp'] = self.timestamp.isoformat()
        d['state'] = self.state.value
        return d
