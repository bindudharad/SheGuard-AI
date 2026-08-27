"""
SheGuard AI+ Orchestrator

Manages agent lifecycle, event routing, and incident state tracking.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum

from core.agent import BaseAgent, AgentMessage, AgentStatus, AgentHealth
from core.event_bus import AgentRegistry, event_bus


class IncidentState(str, Enum):
    NEW = "NEW"
    MONITORING = "MONITORING"
    ELEVATED = "ELEVATED"
    HIGH_RISK = "HIGH_RISK"
    CRITICAL = "CRITICAL"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


@dataclass
class IncidentContext:
    incident_id: str
    trace_id: str
    state: IncidentState = IncidentState.NEW
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    vision_data: Optional[Dict[str, Any]] = None
    audio_data: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    threat_data: Optional[Dict[str, Any]] = None
    decision_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    intelligence_data: Optional[Dict[str, Any]] = None

    last_decision: Optional[str] = None
    pending_intelligence: bool = False
    intelligence_requests: int = 0
    cooldown_until: Optional[datetime] = None

    metadata: Dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    def __init__(self):
        self.registry = AgentRegistry.default()
        self.incidents: Dict[str, IncidentContext] = {}
        self._running = False
        self._subscriptions: List[asyncio.Queue] = []
        self._agents: Dict[str, BaseAgent] = {}
        self.max_intelligence_requests = 1
        self.cooldown_seconds = 60
        self._incident_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        event_types = [
            "FRAME_PROCESSED",
            "AUDIO_PROCESSED",
            "CONTEXT_UPDATED",
            "THREAT_UPDATED",
            "THREAT_ESCALATED",
            "DECISION_MADE",
            "EMERGENCY_DECLARED",
            "ADDITIONAL_INTELLIGENCE_REQUIRED",
            "INTELLIGENCE_RECEIVED",
            "CREATE_INCIDENT",
            "RESPONSE_COMPLETE",
            "RESPONSE_FAILED",
            "EMERGENCY_RESPONSE_FAILED",
            "INCIDENT_RESOLVED",
        ]
        for event_type in event_types:
            queue = await event_bus.subscribe(event_type)
            self._subscriptions.append(queue)
            asyncio.create_task(self._event_listener(event_type, queue))
        print(f"[Orchestrator] Started, subscribed to {len(event_types)} event types")

    async def stop(self) -> None:
        self._running = False
        print("[Orchestrator] Stopped")

    async def register_agent(self, agent: BaseAgent) -> None:
        await self.registry.register(agent)
        self._agents[agent.name] = agent
        print(f"[Orchestrator] Registered agent: {agent.name}")

    async def unregister_agent(self, name: str) -> None:
        await self.registry.unregister(name)
        self._agents.pop(name, None)

    async def _event_listener(self, event_type: str, queue: asyncio.Queue) -> None:
        while self._running:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=1.0)
                await self._route_event(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"[Orchestrator] Error in listener {event_type}: {e}")

    async def _route_event(self, message: AgentMessage) -> None:
        if message.incident_id:
            await self._update_incident(message)
        if message.event_type == "FRAME_PROCESSED":
            await self._handle_vision(message)
        elif message.event_type == "AUDIO_PROCESSED":
            await self._handle_audio(message)
        elif message.event_type == "CONTEXT_UPDATED":
            await self._handle_context(message)
        elif message.event_type in ("THREAT_UPDATED", "THREAT_ESCALATED"):
            await self._handle_threat(message)
        elif message.event_type == "DECISION_MADE":
            await self._handle_decision(message)
        elif message.event_type == "EMERGENCY_DECLARED":
            await self._handle_emergency(message)
        elif message.event_type == "ADDITIONAL_INTELLIGENCE_REQUIRED":
            await self._request_intelligence(message.incident_id, message.trace_id)
        elif message.event_type == "INTELLIGENCE_RECEIVED":
            await self._handle_intelligence_response(message)
        elif message.event_type == "RESPONSE_COMPLETE":
            print(f"[Orchestrator] Response complete {message.incident_id}: {message.data.get('status')}")
        elif message.event_type == "INCIDENT_RESOLVED":
            if message.incident_id in self.incidents:
                self.incidents[message.incident_id].state = IncidentState.RESOLVED

    async def _update_incident(self, message: AgentMessage) -> None:
        async with self._incident_lock:
            iid = message.incident_id
            if iid not in self.incidents:
                self.incidents[iid] = IncidentContext(iid, message.trace_id or str(uuid.uuid4()))
            inc = self.incidents[iid]
            inc.updated_at = datetime.utcnow()
            src = {
                "vision_agent": "vision_data",
                "audio_agent": "audio_data",
                "context_agent": "context_data",
                "threat_agent": "threat_data",
                "decision_agent": "decision_data",
                "response_agent": "response_data",
                "x402_agent": "intelligence_data",
            }.get(message.agent)
            if src:
                setattr(inc, src, message.data)

    async def _handle_vision(self, message: AgentMessage) -> None:
        if not message.incident_id:
            return
        # Vision output uses nested structures: interaction.detected, activity.label
        interaction = message.data.get("interaction", {})
        activity = message.data.get("activity", {})
        context_msg = AgentMessage.create(
            agent="orchestrator",
            event_type="CONTEXT_REQUEST",
            data={
                "incident_id": message.incident_id,
                "trace_id": message.trace_id,
                "camera_id": message.data.get("camera_id"),
                "persons_detected": message.data.get("persons_detected", 0),
                "interaction_detected": interaction.get("detected", False) if isinstance(interaction, dict) else False,
                "activity_label": activity.get("label") if isinstance(activity, dict) else None,
            },
            incident_id=message.incident_id,
            trace_id=message.trace_id,
        )
        await self._process_agent("context_agent", context_msg)

    async def _handle_audio(self, message: AgentMessage) -> None:
        await self._maybe_request_threat_assessment(message.incident_id, message.trace_id)

    async def _handle_context(self, message: AgentMessage) -> None:
        await self._maybe_request_threat_assessment(message.incident_id, message.trace_id)

    async def _maybe_request_threat_assessment(self, incident_id, trace_id) -> None:
        if not incident_id or incident_id not in self.incidents:
            return
        inc = self.incidents[incident_id]
        if inc.vision_data and inc.context_data:
            # Transform vision data to ThreatRequest format (flat structure)
            vd = inc.vision_data
            interaction = vd.get("interaction", {})
            activity = vd.get("activity", {})
            vision_req = {
                "agent": "vision_agent",
                "timestamp": vd.get("timestamp", datetime.utcnow().isoformat()),
                "persons_detected": vd.get("persons_detected", 0),
                "interaction_detected": interaction.get("detected", False) if isinstance(interaction, dict) else False,
                "interaction_confidence": interaction.get("confidence", 0.0) if isinstance(interaction, dict) else 0.0,
                "activity_label": activity.get("label") if isinstance(activity, dict) else None,
                "activity_confidence": activity.get("confidence", 0.0) if isinstance(activity, dict) else 0.0,
                "temporal_confidence": activity.get("temporal_confidence", 0.0) if isinstance(activity, dict) else 0.0,
                "visual_risk_signal": vd.get("visual_risk_signal", 0.0),
                "evidence": vd.get("evidence", []),
                "simulation": vd.get("simulation", False),
            }
            # Transform context data
            cd = inc.context_data
            if "timestamp" in cd and hasattr(cd["timestamp"], "isoformat"):
                cd = dict(cd)
                cd["timestamp"] = cd["timestamp"].isoformat()
            context_req = {
                "agent": "context_agent",
                "timestamp": cd.get("timestamp", datetime.utcnow().isoformat()),
                "context_score": cd.get("context_score", 0.0),
                "context_confidence": cd.get("context_confidence", 0.0),
                "data_quality": cd.get("data_quality", 0.0),
                "time_period": cd.get("time_period"),
                "isolation_status": cd.get("isolation_status"),
                "nearby_incidents": cd.get("nearby_incidents", 0),
                "security_distance_meters": cd.get("security_distance_meters"),
                "reasons": cd.get("reasons", []),
                "simulation": cd.get("simulation", False),
            }
            req = {
                "incident_id": incident_id,
                "trace_id": trace_id or inc.trace_id,
                "vision": vision_req,
                "context": context_req,
                "simulation": inc.vision_data.get("simulation", False),
            }
            if inc.audio_data:
                audio_data = dict(inc.audio_data)
                if "timestamp" in audio_data and hasattr(audio_data["timestamp"], "isoformat"):
                    audio_data["timestamp"] = audio_data["timestamp"].isoformat()
                req["audio"] = audio_data
            msg = AgentMessage.create(
                agent="orchestrator", event_type="THREAT_ASSESS", data=req,
                incident_id=incident_id, trace_id=trace_id or inc.trace_id,
            )
            await self._process_agent("threat_agent", msg)

    async def _handle_threat(self, message: AgentMessage) -> None:
        if not message.incident_id:
            return
        msg = AgentMessage.create(
            agent="orchestrator", event_type="THREAT_UPDATED",
            data={
                "incident_id": message.incident_id,
                "trace_id": message.trace_id,
                "risk_score": message.data.get("risk_score", 0),
                "threat_level": message.data.get("threat_level", "SAFE"),
                "threat_type": message.data.get("threat_type", "none"),
                "confidence": message.data.get("confidence", 0),
                "vision_available": True,
                "audio_available": bool(message.data.get("audio")),
                "context_available": True,
                "uncertainty": 1.0 - message.data.get("confidence", 0),
                "previous_decisions": 0,
                "timestamp": datetime.utcnow(),
                "simulation": message.data.get("simulation", False),
            },
            incident_id=message.incident_id,
            trace_id=message.trace_id,
            confidence=message.data.get("confidence", 0),
        )
        await self._process_agent("decision_agent", msg)

    async def _handle_decision(self, message: AgentMessage) -> None:
        if not message.incident_id:
            return
        decision = message.data.get("decision")
        if message.incident_id in self.incidents:
            self.incidents[message.incident_id].last_decision = decision
        if decision == "REQUEST_ADDITIONAL_INTELLIGENCE":
            await self._request_intelligence(message.incident_id, message.trace_id)
        elif decision in ("CREATE_INCIDENT", "EMERGENCY_RESPONSE"):
            await self._request_response(message.incident_id, message.trace_id, message.data, decision == "EMERGENCY_RESPONSE")

    async def _handle_emergency(self, message: AgentMessage) -> None:
        if message.incident_id:
            await self._request_response(message.incident_id, message.trace_id, message.data, emergency=True)

    async def _request_intelligence(self, incident_id, trace_id) -> None:
        if not incident_id or incident_id not in self.incidents:
            return
        inc = self.incidents[incident_id]
        if inc.intelligence_requests >= self.max_intelligence_requests:
            return
        inc.intelligence_requests += 1
        inc.pending_intelligence = True
        msg = AgentMessage.create(
            agent="orchestrator", event_type="ADDITIONAL_INTELLIGENCE_REQUIRED",
            data={"incident_id": incident_id, "trace_id": trace_id or inc.trace_id,
                  "service": "safety-intelligence", "reason": "insufficient confidence"},
            incident_id=incident_id, trace_id=trace_id or inc.trace_id,
        )
        await self._process_agent("x402_agent", msg)

    async def _handle_intelligence_response(self, message: AgentMessage) -> None:
        if not message.incident_id or message.incident_id not in self.incidents:
            return
        inc = self.incidents[message.incident_id]
        inc.pending_intelligence = False
        inc.intelligence_data = message.data
        
        # Transform vision data to ThreatRequest format
        vision_req = None
        if inc.vision_data:
            vd = inc.vision_data
            interaction = vd.get("interaction", {})
            activity = vd.get("activity", {})
            vision_req = {
                "agent": "vision_agent",
                "timestamp": vd.get("timestamp", datetime.utcnow().isoformat()),
                "persons_detected": vd.get("persons_detected", 0),
                "interaction_detected": interaction.get("detected", False) if isinstance(interaction, dict) else False,
                "interaction_confidence": interaction.get("confidence", 0.0) if isinstance(interaction, dict) else 0.0,
                "activity_label": activity.get("label") if isinstance(activity, dict) else None,
                "activity_confidence": activity.get("confidence", 0.0) if isinstance(activity, dict) else 0.0,
                "temporal_confidence": activity.get("temporal_confidence", 0.0) if isinstance(activity, dict) else 0.0,
                "visual_risk_signal": vd.get("visual_risk_signal", 0.0),
                "evidence": vd.get("evidence", []),
                "simulation": vd.get("simulation", False),
            }
        
        # Transform context data
        context_req = None
        if inc.context_data:
            cd = inc.context_data
            if "timestamp" in cd and hasattr(cd["timestamp"], "isoformat"):
                cd = dict(cd)
                cd["timestamp"] = cd["timestamp"].isoformat()
            context_req = {
                "agent": "context_agent",
                "timestamp": cd.get("timestamp", datetime.utcnow().isoformat()),
                "context_score": cd.get("context_score", 0.0),
                "context_confidence": cd.get("context_confidence", 0.0),
                "data_quality": cd.get("data_quality", 0.0),
                "time_period": cd.get("time_period"),
                "isolation_status": cd.get("isolation_status"),
                "nearby_incidents": cd.get("nearby_incidents", 0),
                "security_distance_meters": cd.get("security_distance_meters"),
                "reasons": cd.get("reasons", []),
                "simulation": cd.get("simulation", False),
            }
        
        req = {
            "incident_id": message.incident_id,
            "trace_id": message.trace_id,
            "vision": vision_req,
            "context": context_req,
            "intelligence": message.data,
            "simulation": inc.vision_data.get("simulation", False) if inc.vision_data else False,
        }
        if inc.audio_data:
            audio_data = dict(inc.audio_data)
            if "timestamp" in audio_data and hasattr(audio_data["timestamp"], "isoformat"):
                audio_data["timestamp"] = audio_data["timestamp"].isoformat()
            req["audio"] = audio_data
        
        msg = AgentMessage.create(
            agent="orchestrator", event_type="THREAT_ASSESS", data=req,
            incident_id=message.incident_id, trace_id=message.trace_id,
        )
        await self._process_agent("threat_agent", msg)

    async def _request_response(self, incident_id, trace_id, decision_data, emergency=False) -> None:
        if not incident_id:
            return
        inc = self.incidents.get(incident_id)
        if not inc:
            return
        msg = AgentMessage.create(
            agent="orchestrator",
            event_type="EMERGENCY_DECLARED" if emergency else "CREATE_INCIDENT",
            data={
                "incident_id": incident_id,
                "trace_id": trace_id or inc.trace_id,
                "decision": decision_data.get("decision", "CREATE_INCIDENT"),
                "risk_score": decision_data.get("risk_score", 0),
                "threat_level": decision_data.get("threat_level", "HIGH"),
                "threat_type": decision_data.get("threat_type", "unknown"),
                "confidence": decision_data.get("confidence", 0),
                "vision_data": inc.vision_data,
                "audio_data": inc.audio_data,
                "context_data": inc.context_data,
                "intelligence_data": inc.intelligence_data,
                "simulation": inc.vision_data.get("simulation", False) if inc.vision_data else False,
            },
            incident_id=incident_id, trace_id=trace_id or inc.trace_id,
        )
        await self._process_agent("response_agent", msg)

    async def _process_agent(self, agent_name: str, message: AgentMessage) -> None:
        agent = await self.registry.get(agent_name)
        if not agent:
            print(f"[Orchestrator] Agent not found: {agent_name}")
            return
        try:
            await agent.process(message)
        except Exception as e:
            print(f"[Orchestrator] Error processing in {agent_name}: {e}")

    async def get_incident_state(self, incident_id: str):
        async with self._incident_lock:
            return self.incidents.get(incident_id)

    async def list_incidents(self) -> List[Dict[str, Any]]:
        async with self._incident_lock:
            return [
                {"incident_id": i.incident_id, "trace_id": i.trace_id, "state": i.state.value,
                 "last_decision": i.last_decision, "pending_intelligence": i.pending_intelligence}
                for i in self.incidents.values()
            ]

    async def health(self) -> Dict[str, Any]:
        agents = await self.registry.list_agents()
        return {"orchestrator": "READY" if self._running else "STOPPED",
                "running": self._running, "active_incidents": len(self.incidents), "agents": agents}


_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
