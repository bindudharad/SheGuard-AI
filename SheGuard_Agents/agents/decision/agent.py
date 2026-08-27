from typing import Optional
from datetime import datetime

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import EventBus
from agents.decision.schemas import DecisionRequest, DecisionResult, DecisionAction, DecisionEvaluation

class DecisionAgent(BaseAgent):
    def __init__(self):
        super().__init__("decision_agent", "2.0.0")
        
    async def _initialize(self) -> None:
        print("[DecisionAgent] Initialized with ThreatFusion integration")
    
    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        if message.event_type == "THREAT_UPDATED" or message.event_type == "THREAT_ESCALATED":
            return await self._make_decision(message)
        if message.event_type == "INTELLIGENCE_RECEIVED":
            return await self._process_intelligence(message)
        return None
    
    async def _make_decision(self, message: AgentMessage) -> AgentMessage:
        request = DecisionRequest(**message.data)
        
        decision = self._evaluate_decision(request)
        
        result = DecisionResult(
            incident_id=request.incident_id,
            trace_id=request.trace_id,
            timestamp=datetime.utcnow(),
            decision=decision.action,
            reasoning=decision.reasoning,
            confidence=decision.confidence,
            required_action=decision.required_action,
            next_agent=decision.next_agent,
            uncertainty=decision.uncertainty
        )
        
        event_type = "DECISION_MADE"
        if result.decision == DecisionAction.EMERGENCY_RESPONSE:
            event_type = "EMERGENCY_DECLARED"
        elif result.decision == DecisionAction.REQUEST_ADDITIONAL_INTELLIGENCE:
            event_type = "ADDITIONAL_INTELLIGENCE_REQUIRED"
        
        await EventBus.publish_event(
            event_type=event_type,
            data=result.to_dict(),
            agent=self.name,
            incident_id=message.incident_id,
            trace_id=message.trace_id,
            confidence=result.confidence
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type=event_type,
            data=result.to_dict(),
            trace_id=message.trace_id,
            confidence=result.confidence
        )
    
    async def _process_intelligence(self, message: AgentMessage) -> AgentMessage:
        data = message.data
        risk_score = data.get("risk_score", 0.0)
        confidence = data.get("confidence", 0.0)
        threat_level = data.get("threat_level", "SAFE")
        
        if risk_score >= 80 and confidence >= 0.85:
            result = DecisionResult(
                decision=DecisionAction.EMERGENCY_RESPONSE,
                reasoning=f"Critical threat confirmed (risk={risk_score:.1f}, conf={confidence:.2f})",
                confidence=confidence,
                required_action="EMERGENCY_RESPONSE",
                next_agent="response_agent",
                uncertainty=1.0 - confidence
            )
        elif risk_score >= 60 and confidence >= 0.70:
            result = DecisionResult(
                decision=DecisionAction.CREATE_INCIDENT,
                reasoning=f"High threat, creating incident (risk={risk_score:.1f}, conf={confidence:.2f})",
                confidence=confidence,
                required_action="CREATE_INCIDENT",
                next_agent="response_agent",
                uncertainty=1.0 - confidence
            )
        else:
            result = DecisionResult(
                decision=DecisionAction.CONTINUE_MONITORING,
                reasoning=f"Threat below threshold (risk={risk_score:.1f}, conf={confidence:.2f})",
                confidence=confidence,
                required_action="NONE",
                next_agent=None,
                uncertainty=1.0 - confidence
            )
        
        await EventBus.publish_event(
            event_type="DECISION_MADE",
            data=result.to_dict(),
            agent=self.name,
            trace_id=message.trace_id,
            confidence=result.confidence
        )
        
        return AgentMessage.create(
            agent=self.name,
            event_type="DECISION_MADE",
            data=result.to_dict(),
            trace_id=message.trace_id,
            confidence=result.confidence
        )
    
    def _evaluate_decision(self, request: DecisionRequest) -> DecisionEvaluation:
        risk = request.risk_score
        conf = request.confidence
        uncertainty = 1.0 - conf
        
        # High risk, high confidence -> emergency response
        if risk >= 80 and conf >= 0.85:
            return DecisionEvaluation(
                action=DecisionAction.EMERGENCY_RESPONSE,
                reasoning=f"Critical risk with high confidence (risk={risk:.1f}, conf={conf:.2f})",
                confidence=conf,
                required_action="EMERGENCY_RESPONSE",
                next_agent="response_agent",
                uncertainty=uncertainty
            )
        
        # High risk but lower confidence -> request additional intelligence
        if risk >= 60 and uncertainty > 0.3:
            return DecisionEvaluation(
                action=DecisionAction.REQUEST_ADDITIONAL_INTELLIGENCE,
                reasoning=f"Risk elevated but confidence insufficient (risk={risk:.1f}, conf={conf:.2f})",
                confidence=conf,
                required_action="REQUEST_ADDITIONAL_INTELLIGENCE",
                next_agent="x402_agent",
                uncertainty=uncertainty
            )
        
        # High risk, moderate confidence -> create incident
        if risk >= 60:
            return DecisionEvaluation(
                action=DecisionAction.CREATE_INCIDENT,
                reasoning=f"High threat, creating incident (risk={risk:.1f}, conf={conf:.2f})",
                confidence=conf,
                required_action="CREATE_INCIDENT",
                next_agent="response_agent",
                uncertainty=uncertainty
            )
        
        # Medium risk -> increase monitoring
        if risk >= 30:
            return DecisionEvaluation(
                action=DecisionAction.INCREASE_MONITORING,
                reasoning=f"Elevated risk, increasing monitoring (risk={risk:.1f}, conf={conf:.2f})",
                confidence=conf,
                required_action="NONE",
                next_agent=None,
                uncertainty=uncertainty
            )
        
        # Low risk -> continue monitoring
        return DecisionEvaluation(
            action=DecisionAction.CONTINUE_MONITORING,
            reasoning=f"Risk within normal range (risk={risk:.1f}, conf={conf:.2f})",
            confidence=conf,
            required_action="NONE",
            next_agent=None,
            uncertainty=uncertainty
        )
    
    async def health(self) -> AgentHealth:
        health = await super().health()
        health.component_status = {
            "decision_engine": "READY",
        }
        return health
    
    async def shutdown(self) -> None:
        await super().shutdown()
        print("[DecisionAgent] Shutdown complete")
