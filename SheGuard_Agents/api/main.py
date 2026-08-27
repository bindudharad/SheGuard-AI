from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uvicorn
import asyncio
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import get_orchestrator, IncidentState
from core.agent import AgentHealth, AgentStatus
from agents.vision.agent import VisionAgent
from agents.vision.config import get_vision_config
from agents.audio.agent import AudioAgent
from agents.audio.config import get_audio_config
from agents.context.agent import ContextAgent
from agents.context.config import get_context_config
from agents.threat.agent import ThreatAgent
from agents.threat.schemas import ThreatWeights
from agents.decision.agent import DecisionAgent
from agents.response.agent import ResponseAgent

from emergency.config import get_emergency_config
from emergency.models import StandardEvent
from emergency.runner import EmergencyRunner, get_runner
from core.event_models import EventType

app = FastAPI(title="SheGuard Agents API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_vision = None
_audio = None
_context = None
_threat = None
_decision = None
_response = None
_orchestrator = None

@app.on_event("startup")
async def startup():
    global _vision, _audio, _context, _threat, _decision, _response, _orchestrator
    
    _vision = VisionAgent(config=get_vision_config())
    _audio = AudioAgent(config=get_audio_config())
    _context = ContextAgent(config=get_context_config())
    _threat = ThreatAgent(weights=ThreatWeights())
    _decision = DecisionAgent()
    _response = ResponseAgent()
    
    await _vision.start()
    await _audio.start()
    await _context.start()
    await _threat.start()
    await _decision.start()
    await _response.start()
    
    runner = get_runner()
    await runner.start()
    _orchestrator = get_orchestrator()

@app.on_event("shutdown")
async def shutdown():
    global _vision, _audio, _context, _threat, _decision, _response, _orchestrator
    
    if _vision:
        await _vision.stop()
    if _audio:
        await _audio.stop()
    if _context:
        await _context.stop()
    if _threat:
        await _threat.stop()
    if _decision:
        await _decision.stop()
    if _response:
        await _response.stop()
    
    runner = get_runner()
    await runner.stop()

@app.get("/health")
async def health():
    return {"status": "ok", "service": "SheGuard Agents API", "version": "1.1.0"}

@app.get("/agents/status")
async def agent_status():
    agents = []
    for agent in [_vision, _audio, _context, _threat, _decision, _response]:
        if agent:
            agents.append({
                "name": agent.name,
                "status": agent.status.value,
                "health": agent.health.value,
                "version": agent.version,
            })
    return {"agents": agents}

@app.post("/incidents/process")
async def process_incident(request: dict):
    incident_id = request.get("incident_id", str(uuid.uuid4()))
    trace_id = str(uuid.uuid4())
    
    vision_msg = await _vision.process_event("FRAME_CAPTURED", {
        "incident_id": incident_id,
        "trace_id": trace_id,
        "frame_data": request.get("frame_data", {}),
    })
    
    return {"incident_id": incident_id, "trace_id": trace_id, "status": "processing"}

@app.post("/emergency/event")
async def handle_emergency_event(event: StandardEvent):
    runner = get_runner()
    result = await runner.orchestrator.handle_event(event)
    return {"processed": result}

@app.get("/emergency/status")
async def emergency_status():
    runner = get_runner()
    return runner.orchestrator.snapshot()

@app.get("/optional/x402/status")
async def x402_status():
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "optional_integrations"))
        from optional_integrations.x402.agent import X402Agent
        return {"available": True, "mode": "simulation"}
    except ImportError:
        return {"available": False, "message": "x402 optional integration not installed"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)

