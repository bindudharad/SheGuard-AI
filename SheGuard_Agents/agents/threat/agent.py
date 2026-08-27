from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import EventBus
from agents.threat.schemas import (
    ThreatRequest, ThreatResult, VisionSignal, AudioSignal, ContextSignal,
    ThreatWeights, ThreatLevel, ThreatType, RiskFactor, RiskContribution
)
from agents.threat.threat_fusion import ThreatFusionEngine, ThreatContribution as FusionContribution

class ThreatAgent(BaseAgent):
    def __init__(self, weights: Optional[ThreatWeights] = None):
        super().__init__("threat_agent", "2.0.0")
        self.weights = weights or ThreatWeights()
        
        # Initialize the new fusion engine
        self.fusion_engine = ThreatFusionEngine(
            vision_weight=self.weights.vision_weight,
            following_weight=0.20,
            approaching_weight=0.10,
            chasing_weight=0.15,
            fleeing_weight=0.10,
            confrontation_weight=0.10,
            audio_weight=self.weights.audio_weight,
            context_weight=self.weights.context_weight,
            safe_max=self.weights.safe_max,
            warning_max=self.weights.warning_max,
            high_max=self.weights.high_max,
            critical_max=self.weights.critical_min,
            emergency_min=90.0,
            smooth_factor=0.7,
            max_increase_per_frame=15.0,
            max_decrease_per_frame=10.0,
        )
        
    async def _initialize(self) -> None:
        print("[ThreatAgent] Initialized with ThreatFusionEngine")
    
    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.event_type == "THREAT_ASSESS":
            return await self._assess_threat(message)
        elif message.event_type == "FRAME_PROCESSED":
            return await self._process_frame_data(message)
        return None
    
    async def _process_frame_data(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Process frame data from VisionAgent and run threat fusion.
        This is the new primary entry point.
        """
        data = message.data
        
        # Extract signals
        vision_signal = data
        following_events = data.get("following", [])
        behaviors = data.get("behaviors", [])
        
        # Run threat fusion
        result = self.fusion_engine.assess(
            vision_signal=vision_signal,
            following_events=following_events,
            behavior_results=behaviors,
            audio_signal=None,  # Could be added from audio agent
            context_signal=None,  # Could be added from context agent
            tracks=data.get("tracking", []),
            now=time.time()
        )
        
        # Convert to ThreatResult schema
        threat_result = ThreatResult(
            incident_id=message.incident_id,
            trace_id=message.trace_id,
            timestamp=datetime.utcnow(),
            risk_score=result.risk_score,
            threat_level=ThreatLevel(result.risk_level),
            threat_type=self._map_type(result.behaviors),
            confidence=result.confidence,
            contributions=self._convert_contributions(result.contributions),
            reasons=result.reasons,
            vision_available=True,
            audio_available=False,
            context_available=False,
            simulation=data.get("simulation", False)
        )
        
        # Determine event type
        event_type = "THREAT_UPDATED"
        if result.risk_level in ("HIGH", "CRITICAL", "EMERGENCY"):
            event_type = "THREAT_ESCALATED"
        
        # Publish to event bus
        await EventBus.publish_event(
            event_type=event_type,
            data=threat_result.to_dict(),
            agent=self.name,
            incident_id=message.incident_id,
            trace_id=message.trace_id,
            confidence=result.confidence
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type=event_type,
            data=threat_result.to_dict(),
            trace_id=message.trace_id,
            confidence=result.confidence
        )
    
    async def _assess_threat(self, message: AgentMessage) -> AgentMessage:
        """Legacy method for backward compatibility"""
        request = ThreatRequest(**message.data)
        
        # Convert legacy request to fusion engine format
        vision = None
        if request.vision:
            vision = request.vision.dict()
        
        # Extract intelligence data into fusion engine format
        following_events = None
        behavior_results = None
        if request.intelligence:
            following_events = request.intelligence.get('following_events')
            behavior_results = request.intelligence.get('behavioral_events')
        
        result = self.fusion_engine.assess(
            vision_signal=vision,
            audio_signal=request.audio.dict() if request.audio else None,
            context_signal=request.context.dict() if request.context else None,
            following_events=following_events,
            behavior_results=behavior_results,
        )
        
        threat_result = ThreatResult(
            incident_id=request.incident_id,
            trace_id=request.trace_id,
            timestamp=datetime.utcnow(),
            risk_score=result.risk_score,
            threat_level=ThreatLevel(result.risk_level),
            threat_type=self._map_type(result.behaviors),
            confidence=result.confidence,
            contributions=self._convert_contributions(result.contributions),
            reasons=result.reasons,
            vision_available=request.vision is not None,
            audio_available=request.audio is not None,
            context_available=request.context is not None,
            simulation=request.simulation
        )
        
        event_type = "THREAT_UPDATED"
        if result.risk_level in ("HIGH", "CRITICAL", "EMERGENCY"):
            event_type = "THREAT_ESCALATED"
        
        await EventBus.publish_event(
            event_type=event_type,
            data=threat_result.to_dict(),
            agent=self.name,
            incident_id=message.incident_id,
            trace_id=message.trace_id,
            confidence=result.confidence
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type=event_type,
            data=threat_result.to_dict(),
            trace_id=message.trace_id,
            confidence=result.confidence
        )
    
    def _map_type(self, behaviors: List[str]) -> ThreatType:
        if not behaviors:
            return ThreatType.NONE
        # Priority order - map to valid ThreatType enums
        if "chasing" in behaviors:
            return ThreatType.POSSIBLE_PHYSICAL_AGGRESSION
        if "following" in behaviors:
            return ThreatType.POSSIBLE_CONFRONTATION
        if "confrontation" in behaviors:
            return ThreatType.POSSIBLE_CONFRONTATION
        if "fleeing" in behaviors:
            return ThreatType.ABNORMAL_MOVEMENT
        if "approaching" in behaviors:
            return ThreatType.POSSIBLE_CONFRONTATION
        if "fall" in behaviors:
            return ThreatType.POSSIBLE_FALL
        if "distress" in behaviors:
            return ThreatType.DISTRESS_KEYWORD
        return ThreatType.ABNORMAL_MOVEMENT
    
    def _convert_contributions(self, contributions: List[FusionContribution]) -> List[RiskContribution]:
        factor_map = {
            "vision": RiskFactor.VISION,
            "following": RiskFactor.VISION,
            "behavior": RiskFactor.VISION,
            "audio": RiskFactor.AUDIO,
            "context": RiskFactor.CONTEXT,
            "gru": RiskFactor.VISION,
        }
        
        result = []
        for c in contributions:
            factor = factor_map.get(c.source, RiskFactor.VISION)
            result.append(RiskContribution(
                factor=factor,
                raw_score=c.raw_score,
                weight=c.weight,
                weighted_score=c.weighted_score,
                confidence=c.confidence,
                evidence=c.evidence,
            ))
        return result
    
    async def health(self) -> AgentHealth:
        health = await super().health()
        health.component_status = {
            "risk_engine": "READY",
            "fusion_engine": "READY",
            "weights_loaded": True,
        }
        return health
    
    async def shutdown(self) -> None:
        await super().shutdown()
        print("[ThreatAgent] Shutdown complete")


import time
