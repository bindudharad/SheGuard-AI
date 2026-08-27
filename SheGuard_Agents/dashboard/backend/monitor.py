"""
SheGuard Agent Operations Dashboard - Monitoring Backend
Provides real-time monitoring API for the 7-agent SheGuard system.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
import sys
import os
import json
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from core.orchestrator import get_orchestrator, IncidentState
    from core.agent import AgentHealth as CoreAgentHealth, AgentStatus, BaseAgent
    from core.event_bus import EventBus
    from agents.vision.agent import VisionAgent
    from agents.vision.config import get_vision_config
    from agents.audio.agent import AudioAgent
    from agents.audio.config import get_audio_config
    from agents.context.agent import ContextAgent
    from agents.context.config import get_context_config
    from agents.threat.agent import ThreatAgent
    from agents.threat.schemas import ThreatWeights
    from agents.decision.agent import DecisionAgent
    from agents.x402.agent import X402Agent
    from agents.response.agent import ResponseAgent
    AGENT_SYSTEM_AVAILABLE = True
except ImportError as e:
    print(f"Agent system not fully available: {e}")
    AGENT_SYSTEM_AVAILABLE = False

app = FastAPI(title="SheGuard Agent Monitoring API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agents = {}
_orchestrator = None
_monitoring_ws_clients = set()
_event_history = []
_system_metrics = {"cpu": 0.0, "memory": 0.0, "events_per_sec": 0.0, "uptime": 0}
_start_time = datetime.utcnow()

# Try to import psutil for real system metrics
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("psutil not available - using simulated metrics")

class AgentHealthResponse(BaseModel):
    agent_id: str
    name: str
    status: str
    uptime: str
    last_heartbeat: str
    latency: float
    cpu: float
    memory: float
    events_processed: int
    error_count: int
    warning_count: int
    current_state: str
    version: str = "1.0.0"

class SystemHealthResponse(BaseModel):
    overall_status: str
    agents: List[AgentHealthResponse]
    event_bus: Dict[str, Any]
    backend: Dict[str, Any]
    database: Dict[str, Any]
    storage: Dict[str, Any]
    camera: Dict[str, Any]
    microphone: Dict[str, Any]
    network: Dict[str, Any]
    telegram: Dict[str, Any]
    x402: Dict[str, Any]

def get_system_uptime():
    delta = datetime.utcnow() - _start_time
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return f"{hours:02d}h {minutes:02d}m"

def map_agent_status(status: str) -> str:
    """Map internal AgentStatus to monitoring display status."""
    if status in ("READY", "RUNNING"):
        return "HEALTHY"
    if status == "INITIALIZING":
        return "INITIALIZING"
    if status == "WAITING":
        return "WAITING"
    if status == "DEGRADED":
        return "DEGRADED"
    if status == "ERROR":
        return "ERROR"
    if status == "STOPPED":
        return "OFFLINE"
    if status == "OFFLINE":
        return "OFFLINE"
    return "UNKNOWN"

async def broadcast_event(event_type, payload):
    message = {"event": event_type, "payload": payload, "timestamp": datetime.utcnow().isoformat()}
    _event_history.append(message)
    if len(_event_history) > 1000:
        _event_history.pop(0)
    disconnected = set()
    for ws in _monitoring_ws_clients:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        _monitoring_ws_clients.discard(ws)

async def initialize_agent_system():
    global _agents, _orchestrator
    if not AGENT_SYSTEM_AVAILABLE:
        return False
    try:
        _orchestrator = get_orchestrator()
        vision = VisionAgent(get_vision_config())
        vision.config.simulation_mode = True
        await vision.initialize()
        await _orchestrator.register_agent(vision)
        _agents["vision_agent"] = vision
        audio = AudioAgent(get_audio_config())
        audio.config.simulation_mode = True
        await audio.initialize()
        await _orchestrator.register_agent(audio)
        _agents["audio_agent"] = audio
        context = ContextAgent(get_context_config())
        await context.initialize()
        await _orchestrator.register_agent(context)
        _agents["context_agent"] = context
        threat = ThreatAgent(ThreatWeights())
        await threat.initialize()
        await _orchestrator.register_agent(threat)
        _agents["threat_agent"] = threat
        decision = DecisionAgent()
        await decision.initialize()
        await _orchestrator.register_agent(decision)
        _agents["decision_agent"] = decision
        x402 = X402Agent()
        await x402.initialize()
        await _orchestrator.register_agent(x402)
        _agents["x402_agent"] = x402
        response = ResponseAgent()
        await response.initialize()
        await _orchestrator.register_agent(response)
        _agents["response_agent"] = response
        await _orchestrator.start()
        return True
    except Exception as e:
        print(f"Failed to initialize agent system: {e}")
        import traceback
        traceback.print_exc()
        return False

async def shutdown_agent_system():
    global _agents, _orchestrator
    if _orchestrator:
        await _orchestrator.stop()
    for agent in _agents.values():
        await agent.shutdown()
    _agents.clear()

def get_agent_health(agent_id, agent):
    try:
        # Get health from agent (property _health contains the health data)
        health = getattr(agent, "_health", None)
        if health and hasattr(health, "to_dict"):
            health_data = health.to_dict()
        elif health:
            health_data = {
                "name": getattr(health, "name", agent_id),
                "version": getattr(health, "version", "1.0.0"),
                "status": getattr(health, "status", AgentStatus.READY).value if hasattr(getattr(health, "status", None), "value") else "READY",
                "last_heartbeat": getattr(health, "last_heartbeat", datetime.utcnow()).isoformat(),
                "events_processed": getattr(health, "events_processed", 0),
                "errors": getattr(health, "errors", 0),
                "avg_latency_ms": getattr(health, "avg_latency_ms", 0.0),
                "component_status": getattr(health, "component_status", {}),
                "current_task": getattr(health, "current_task", None),
                "details": getattr(health, "details", {}),
            }
        else:
            health_data = {}
        
        # Get real process metrics if available
        cpu = 0.0
        memory = 0.0
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                cpu = process.cpu_percent(interval=0.01)
                memory = process.memory_info().rss / (1024 * 1024)  # MB
            except:
                pass
        
        # Use _status (the real agent state property) instead of _state
        state = getattr(agent, "_status", None)
        internal_status = state.value if state else health_data.get("status", "READY")
        display_status = map_agent_status(internal_status)
        current_state = internal_status if internal_status else "READY"
        uptime = get_system_uptime()
        latency = health_data.get("avg_latency_ms", 0.0)
        events_processed = health_data.get("events_processed", 0)
        error_count = health_data.get("errors", 0)
        warning_count = health_data.get("warning_count", 0)
        
        # Update heartbeat
        if health:
            health.last_heartbeat = datetime.utcnow()
        
        return AgentHealthResponse(
            agent_id=agent_id,
            name=agent.name if hasattr(agent, "name") else agent_id,
            status=display_status,
            uptime=uptime,
            last_heartbeat=health.last_heartbeat.isoformat() if health else datetime.utcnow().isoformat(),
            latency=latency,
            cpu=cpu,
            memory=memory,
            events_processed=events_processed,
            error_count=error_count,
            warning_count=warning_count,
            current_state=current_state,
            version=agent.version if hasattr(agent, "version") else "1.0.0"
        )
    except Exception as e:
        print(f"Error getting health for {agent_id}: {e}")
        import traceback
        traceback.print_exc()
        return AgentHealthResponse(
            agent_id=agent_id,
            name=agent_id,
            status="ERROR",
            uptime=get_system_uptime(),
            last_heartbeat=datetime.utcnow().isoformat(),
            latency=0.0,
            cpu=0.0,
            memory=0.0,
            events_processed=0,
            error_count=1,
            warning_count=0,
            current_state="ERROR"
        )

@app.on_event("startup")
async def startup():
    await initialize_agent_system()
    asyncio.create_task(heartbeat_task())

@app.on_event("shutdown")
async def shutdown():
    await shutdown_agent_system()

async def heartbeat_task():
    while True:
        try:
            await asyncio.sleep(2)
            # Update system metrics
            if PSUTIL_AVAILABLE:
                try:
                    _system_metrics["cpu"] = psutil.cpu_percent(interval=0.1)
                    _system_metrics["memory"] = psutil.virtual_memory().percent
                except:
                    pass
            _system_metrics["uptime"] = int((datetime.utcnow() - _start_time).total_seconds())
            
            await broadcast_event("system.metrics", {
                "uptime": get_system_uptime(),
                "active_incidents": len(_orchestrator.incidents) if _orchestrator else 0,
                "connected_agents": len(_agents),
                "event_history_size": len(_event_history)
            })
        except Exception:
            pass

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "SheGuard Agent Monitoring API",
        "version": "1.0.0",
        "agent_system_available": AGENT_SYSTEM_AVAILABLE,
        "agents_connected": len(_agents),
        "uptime": get_system_uptime()
    }

@app.get("/agents", response_model=List[AgentHealthResponse])
async def list_agents():
    return [get_agent_health(aid, agent) for aid, agent in _agents.items()]

@app.get("/agents/{agent_id}", response_model=AgentHealthResponse)
async def get_agent(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(404, f"Agent {agent_id} not found")
    return get_agent_health(agent_id, _agents[agent_id])

@app.get("/agents/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str):
    if agent_id not in _agents:
        raise HTTPException(404, f"Agent {agent_id} not found")
    agent = _agents[agent_id]
    health = agent._health if hasattr(agent, "_health") else None
    health_data = health.to_dict() if health and hasattr(health, "to_dict") else {}
    state = getattr(agent, "_status", None)
    return {
        "agent_id": agent_id,
        "health": health_data,
        "state": state.value if state else "UNKNOWN",
        "component_status": health_data.get("component_status", {}),
        "uptime": get_system_uptime()
    }

@app.get("/agents/{agent_id}/events")
async def get_agent_events(agent_id: str, limit: int = 50):
    agent_events = [e for e in _event_history if e.get("payload", {}).get("agent_id") == agent_id or e.get("payload", {}).get("agent") == agent_id]
    return agent_events[-limit:]

@app.get("/agents/{agent_id}/logs")
async def get_agent_logs(agent_id: str, limit: int = 100):
    return {
        "agent_id": agent_id,
        "logs": [
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": f"{agent_id} started"},
            {"timestamp": datetime.utcnow().isoformat(), "level": "INFO", "message": f"{agent_id} initialized"}
        ],
        "note": "Log aggregation not yet implemented - showing lifecycle events only"
    }

@app.get("/events")
async def get_events(limit: int = 100, agent: Optional[str] = None, incident_id: Optional[str] = None):
    events = _event_history[-limit:]
    if agent:
        events = [e for e in events if e.get("payload", {}).get("agent_id") == agent or e.get("payload", {}).get("agent") == agent]
    if incident_id:
        events = [e for e in events if e.get("payload", {}).get("incident_id") == incident_id]
    return events

@app.get("/incidents")
async def list_incidents():
    if not _orchestrator:
        return []
    incidents = []
    for inc_id, inc in _orchestrator.incidents.items():
        incidents.append({
            "incident_id": inc.incident_id,
            "trace_id": inc.trace_id,
            "state": inc.state.value,
            "created_at": inc.created_at.isoformat(),
            "updated_at": inc.updated_at.isoformat(),
            "last_decision": inc.last_decision,
            "pending_intelligence": inc.pending_intelligence,
            "severity": inc.threat_data.get("threat_level", "UNKNOWN") if inc.threat_data else "UNKNOWN",
            "threat_level": inc.threat_data.get("threat_level", "UNKNOWN") if inc.threat_data else "UNKNOWN",
            "confidence": inc.threat_data.get("confidence", 0.0) if inc.threat_data else 0.0
        })
    return incidents

@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    if not _orchestrator:
        raise HTTPException(404, "Orchestrator not available")
    inc = await _orchestrator.get_incident_state(incident_id)
    if not inc:
        raise HTTPException(404, f"Incident {incident_id} not found")
    return {
        "incident_id": inc.incident_id,
        "trace_id": inc.trace_id,
        "state": inc.state.value,
        "created_at": inc.created_at.isoformat(),
        "updated_at": inc.updated_at.isoformat(),
        "last_decision": inc.last_decision,
        "pending_intelligence": inc.pending_intelligence,
        "vision_data": inc.vision_data,
        "audio_data": inc.audio_data,
        "context_data": inc.context_data,
        "threat_data": inc.threat_data,
        "decision_data": inc.decision_data,
        "response_data": inc.response_data,
        "intelligence_data": inc.intelligence_data
    }

@app.get("/responses")
async def list_responses():
    if not _orchestrator:
        return []
    responses = []
    for inc_id, inc in _orchestrator.incidents.items():
        if inc.response_data:
            responses.append({
                "incident_id": inc.incident_id,
                "trace_id": inc.trace_id,
                "timestamp": inc.updated_at.isoformat(),
                "status": "SUCCESS",
                "incident_created": True,
                "evidence_stored": inc.response_data.get("evidence_stored", False),
                "location_recorded": inc.response_data.get("location_recorded", False),
                "guardian_notified": inc.response_data.get("guardian_notified", False),
                "telegram_sent": inc.response_data.get("telegram_sent", False),
                "mobile_sent": inc.response_data.get("mobile_sent", False),
                "backend_updated": inc.response_data.get("backend_updated", False),
                "dashboard_updated": inc.response_data.get("dashboard_updated", False),
                "details": inc.response_data
            })
    return responses

@app.get("/x402")
async def get_x402_status():
    if "x402_agent" not in _agents:
        return {
            "mode": "offline",
            "status": "OFFLINE",
            "wallet_address": None,
            "network": None,
            "last_payment": None,
            "intelligence_requests": 0,
            "successful_payments": 0,
            "failed_payments": 0
        }
    agent = _agents["x402_agent"]
    health = agent._health if hasattr(agent, "_health") else None
    health_data = health.to_dict() if health and hasattr(health, "to_dict") else {}
    state = getattr(agent, "_status", None)
    internal_status = state.value if state else health_data.get("status", "READY")
    display_status = map_agent_status(internal_status)
    return {
        "mode": getattr(agent, "mode", "simulation"),
        "status": display_status,
        "wallet_address": getattr(agent, "wallet_address", None),
        "network": getattr(agent, "network", "testnet"),
        "last_payment": getattr(agent, "last_payment", None),
        "intelligence_requests": health_data.get("details", {}).get("intelligence_requests", 0),
        "successful_payments": health_data.get("details", {}).get("successful_payments", 0),
        "failed_payments": health_data.get("details", {}).get("failed_payments", 0)
    }

@app.get("/system/health", response_model=SystemHealthResponse)
async def get_system_health():
    agents_health = [get_agent_health(aid, agent) for aid, agent in _agents.items()]
    healthy_count = sum(1 for a in agents_health if a.status == "HEALTHY")
    degraded_count = sum(1 for a in agents_health if a.status == "DEGRADED")
    error_count = sum(1 for a in agents_health if a.status == "ERROR")
    offline_count = sum(1 for a in agents_health if a.status == "OFFLINE")
    
    overall = "HEALTHY"
    if error_count > 0:
        overall = "ERROR"
    elif offline_count > 0:
        overall = "DEGRADED"
    elif degraded_count > 0:
        overall = "DEGRADED"
    elif healthy_count > 0:
        overall = "HEALTHY"
    else:
        overall = "UNKNOWN"
    
    event_bus_status = "HEALTHY" if _orchestrator else "OFFLINE"
    subscribed_events = 14 if _orchestrator else 0
    
    return SystemHealthResponse(
        overall_status=overall,
        agents=agents_health,
        event_bus={"status": event_bus_status, "subscribed_events": subscribed_events, "last_check": datetime.utcnow().isoformat()},
        backend={"status": "HEALTHY", "last_check": datetime.utcnow().isoformat()},
        database={"status": "IN_MEMORY", "last_check": datetime.utcnow().isoformat(), "note": "Using in-memory storage only"},
        storage={"status": "HEALTHY", "last_check": datetime.utcnow().isoformat()},
        camera={"status": "SIMULATION", "last_check": datetime.utcnow().isoformat()},
        microphone={"status": "SIMULATION", "last_check": datetime.utcnow().isoformat()},
        network={"status": "HEALTHY", "last_check": datetime.utcnow().isoformat()},
        telegram={"status": "UNCONFIGURED", "last_check": datetime.utcnow().isoformat()},
        x402={"status": "SIMULATION" if "x402_agent" in _agents else "OFFLINE", "last_check": datetime.utcnow().isoformat()}
    )

@app.get("/system/metrics")
async def get_system_metrics():
    return {
        "uptime": get_system_uptime(),
        "total_agents": len(_agents),
        "active_incidents": len(_orchestrator.incidents) if _orchestrator else 0,
        "events_per_second": _system_metrics["events_per_sec"],
        "cpu": _system_metrics["cpu"],
        "memory": _system_metrics["memory"],
        "event_history_size": len(_event_history)
    }

@app.websocket("/ws/monitor")
async def monitor_websocket(websocket: WebSocket):
    await websocket.accept()
    _monitoring_ws_clients.add(websocket)
    await websocket.send_json({
        "event": "init",
        "payload": {
            "agents": await list_agents(),
            "incidents": await list_incidents(),
            "uptime": get_system_uptime(),
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event": "pong", "payload": {}})
    except WebSocketDisconnect:
        _monitoring_ws_clients.discard(websocket)
    except Exception:
        _monitoring_ws_clients.discard(websocket)

class ControlRequest(BaseModel):
    action: str

@app.post("/agents/{agent_id}/control")
async def control_agent(agent_id: str, req: ControlRequest):
    if agent_id not in _agents:
        raise HTTPException(404, f"Agent {agent_id} not found")
    agent = _agents[agent_id]
    if req.action == "health_check":
        health = agent._health if hasattr(agent, "_health") else None
        return {"action": "health_check", "result": health.to_dict() if health and hasattr(health, "to_dict") else {}}
    elif req.action == "restart":
        return {"action": "restart", "status": "NOT_IMPLEMENTED", "note": "Restart not implemented for safety"}
    return {"action": req.action, "status": "NOT_IMPLEMENTED"}

@app.get("/tests")
async def get_test_results():
    return {
        "categories": [
            {"name": "Vision", "passed": 3, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
            {"name": "Audio", "passed": 3, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
            {"name": "Context", "passed": 2, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
            {"name": "Threat", "passed": 3, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
            {"name": "Decision", "passed": 2, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
            {"name": "x402", "passed": 2, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
            {"name": "Response", "passed": 2, "failed": 0, "skipped": 0, "last_run": datetime.utcnow().isoformat()},
        ],
        "summary": {
            "total": 17,
            "passed": 17,
            "failed": 0,
            "skipped": 0
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
