"""Agent orchestration sync endpoints (additive, non-breaking).

Allows the SheGuard_Agents orchestrator to coordinate emergency state with the
backend using either the shared AI-engine service token or a normal user JWT.
All writes reuse the existing models/services - no database migration needed.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CCTVCamera, EmergencyNotification, EmergencySession, Incident, TrackingSession, User
from app.services.auth import get_service_or_user
from app.services.emergency_session_manager import EmergencySessionManager
from app.services.realtime import realtime_hub


router = APIRouter(tags=["agents"])
sessions = EmergencySessionManager()

AGENT_STATE_EVENT = "incident.updated"
POLICE_ALERT_EVENT = "police_alert"


def camera_out(row: CCTVCamera) -> dict:
    return {
        "camera_id": row.camera_id,
        "camera_name": row.camera_name,
        "ip_address": row.ip_address,
        "rtsp_url": row.rtsp_url,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "online_status": row.online_status,
    }


class AgentEmergencyStart(BaseModel):
    user_id: int
    session_id: Optional[str] = None
    incident_id: Optional[int] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    trigger_source: str = "agent_orchestrator"


class AgentStateUpdate(BaseModel):
    """Orchestration state pushed by SheGuard_Agents for one incident/session."""
    incident_id: Optional[int] = None
    session_id: Optional[str] = None
    state: Optional[str] = None
    threat_level: Optional[str] = None
    threat_score: Optional[float] = None
    priority: Optional[str] = None
    ai_result: Optional[str] = None
    ai_confidence: Optional[float] = None
    ai_unavailable: Optional[bool] = None
    cameras: Optional[list[dict[str, Any]]] = None
    tracking_status: Optional[str] = None
    timeline_event: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class PoliceAlertRequest(BaseModel):
    incident_id: Optional[int] = None
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    threat_level: str = "HIGH"
    priority_score: Optional[float] = None
    message: Optional[str] = None
    cameras: Optional[list[dict[str, Any]]] = None


def _timeline(session: EmergencySession) -> list[dict]:
    if not session.timeline_json:
        return []
    try:
        return json.loads(session.timeline_json)
    except json.JSONDecodeError:
        return []


@router.post("/agents/emergency/start")
def agent_start_emergency(
    payload: AgentEmergencyStart,
    db: Session = Depends(get_db),
    _auth=Depends(get_service_or_user),
):
    """Create/refresh an EmergencySession on behalf of an app user."""
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    incident = db.get(Incident, payload.incident_id) if payload.incident_id else None
    if payload.incident_id and not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # If this user already has an active session for a different id keep it -
    # never overwrite another active emergency (multi-user safety).
    if payload.session_id:
        existing = db.get(EmergencySession, payload.session_id)
        if existing and existing.status == "active" and existing.user_id != payload.user_id:
            raise HTTPException(status_code=409, detail="Session id already owned by another user")

    session = sessions.start_session(
        db,
        user=user,
        incident=incident,
        session_id=payload.session_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        trigger_source=payload.trigger_source,
    )
    db.commit()
    db.refresh(session)
    return {"status": "active", "session": sessions.session_payload(session, incident)}


@router.get("/agents/live")
def agent_live_snapshot(db: Session = Depends(get_db), _auth=Depends(get_service_or_user)):
    """Snapshot of everything the orchestrator needs to reconcile on startup."""
    active_sessions = db.scalars(
        select(EmergencySession).where(EmergencySession.status == "active").order_by(EmergencySession.started_at.desc())
    ).all()
    recent_incidents = db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(25)).all()
    tracking = db.scalars(
        select(TrackingSession).where(TrackingSession.status == "active").order_by(TrackingSession.started_at.desc()).limit(50)
    ).all()

    def inc_out(i: Incident) -> dict:
        return {
            "incident_id": i.incident_id,
            "user_id": i.user_id,
            "incident_type": i.incident_type,
            "confidence": i.confidence,
            "threat_level": i.threat_level,
            "threat_score": i.threat_score,
            "camera_id": i.camera_id,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "status": i.status,
            "emergency_session_id": i.emergency_session_id,
            "created_at": i.created_at.isoformat() if i.created_at else None,
        }

    return {
        "emergency_sessions": [sessions.session_payload(s) for s in active_sessions],
        "recent_incidents": [inc_out(i) for i in recent_incidents],
        "active_tracking": [
            {
                "session_id": t.session_id,
                "user_id": t.user_id,
                "status": t.status,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "last_update_at": t.last_update_at.isoformat() if t.last_update_at else None,
                "latitude": t.last_latitude,
                "longitude": t.last_longitude,
            }
            for t in tracking
        ],
    }


@router.post("/agents/state")
def agent_push_state(payload: AgentStateUpdate, db: Session = Depends(get_db), _auth=Depends(get_service_or_user)):
    """Persist orchestration state onto the incident row (existing JSON columns)
    and broadcast `incident.updated` so the dashboard can refresh instantly."""
    incident: Incident | None = None
    if payload.incident_id is not None:
        incident = db.get(Incident, payload.incident_id)
        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")
    elif payload.session_id:
        incident = db.scalars(
            select(Incident).where(Incident.emergency_session_id == payload.session_id).order_by(Incident.created_at.desc())
        ).first()

    session: EmergencySession | None = None
    if payload.session_id:
        session = db.get(EmergencySession, payload.session_id)

    if incident is None and session is None:
        raise HTTPException(status_code=404, detail="No incident or emergency session matches the update")

    now_iso = datetime.utcnow().isoformat()
    event = {
        "state": payload.state,
        "threat_level": payload.threat_level,
        "threat_score": payload.threat_score,
        "priority": payload.priority,
        "ai_result": payload.ai_result,
        "ai_confidence": payload.ai_confidence,
        "ai_unavailable": payload.ai_unavailable,
        "tracking_status": payload.tracking_status,
        "cameras": payload.cameras,
        "at": now_iso,
        **({"timeline_event": payload.timeline_event} if payload.timeline_event else {}),
        **({"metadata": payload.metadata} if payload.metadata else {}),
    }
    event = {k: v for k, v in event.items() if v is not None}

    if incident is not None:
        timeline = list(incident.agent_timeline or [])
        timeline.append(event)
        incident.agent_timeline = timeline[-100:]

        risk_reasons = dict(incident.risk_reasons or {})
        if payload.threat_level is not None:
            risk_reasons["orchestrator_threat_level"] = payload.threat_level
        if payload.threat_score is not None:
            risk_reasons["orchestrator_threat_score"] = payload.threat_score
        if payload.cameras is not None:
            risk_reasons["associated_cameras"] = payload.cameras
        if payload.metadata:
            for key, value in payload.metadata.items():
                risk_reasons[f"orchestrator_{key}"] = value
        if risk_reasons:
            incident.risk_reasons = risk_reasons

        intelligence = dict(incident.intelligence_result or {})
        if payload.ai_result is not None or payload.ai_confidence is not None or payload.ai_unavailable is not None:
            intelligence.update(
                {
                    "ai_result": payload.ai_result if payload.ai_result is not None else intelligence.get("ai_result"),
                    "ai_confidence": payload.ai_confidence if payload.ai_confidence is not None else intelligence.get("ai_confidence"),
                    "ai_unavailable": payload.ai_unavailable if payload.ai_unavailable is not None else intelligence.get("ai_unavailable"),
                    "updated_at": now_iso,
                }
            )
            incident.intelligence_result = intelligence

        if payload.state is not None:
            incident.status = payload.state

        if session is None and incident.emergency_session_id:
            session = db.get(EmergencySession, incident.emergency_session_id)

    if session is not None:
        timeline = _timeline(session)
        timeline.append({"event": "agent.state", "at": now_iso, **event})
        session.timeline_json = json.dumps(timeline[-100:], ensure_ascii=True)
        if payload.state in ("POLICE_ALERTED",):
            session.status = session.status if session.status != "active" else "active"

    db.commit()

    broadcast_payload = {
        "incident_id": incident.incident_id if incident else None,
        "session_id": payload.session_id or (incident.emergency_session_id if incident else None),
        "user_id": incident.user_id if incident else (session.user_id if session else None),
        **event,
    }
    realtime_hub.publish_from_sync(AGENT_STATE_EVENT, broadcast_payload)
    if broadcast_payload["session_id"]:
        realtime_hub.publish_session_from_sync(broadcast_payload["session_id"], AGENT_STATE_EVENT, broadcast_payload)
    return {"status": "ok", "broadcast": broadcast_payload}


@router.post("/agents/police-alert")
def agent_police_alert(payload: PoliceAlertRequest, db: Session = Depends(get_db), _auth=Depends(get_service_or_user)):
    """Record + broadcast a police alert generated by the agents orchestrator."""
    incident: Incident | None = None
    if payload.incident_id is not None:
        incident = db.get(Incident, payload.incident_id)
    elif payload.session_id:
        incident = db.scalars(
            select(Incident).where(Incident.emergency_session_id == payload.session_id).order_by(Incident.created_at.desc())
        ).first()

    session: EmergencySession | None = None
    if payload.session_id:
        session = db.get(EmergencySession, payload.session_id)
    if session is None and incident and incident.emergency_session_id:
        session = db.get(EmergencySession, incident.emergency_session_id)

    notification = EmergencyNotification(
        incident_id=incident.incident_id if incident else None,
        emergency_session_id=payload.session_id or (session.session_id if session else None),
        user_id=payload.user_id or (incident.user_id if incident else (session.user_id if session else None)),
        channel="police_dashboard",
        recipient="command_center",
        status="sent",
        message=payload.message
        or f"[{payload.threat_level}] Police alert published by agents orchestrator"
        + (f" score={payload.priority_score}" if payload.priority_score is not None else ""),
        sent_at=datetime.utcnow(),
    )
    db.add(notification)
    if incident is not None:
        timeline = list(incident.agent_timeline or [])
        timeline.append({"police_alert": True, "threat_level": payload.threat_level, "at": datetime.utcnow().isoformat()})
        incident.agent_timeline = timeline[-100:]
    if session is not None:
        timeline = _timeline(session)
        timeline.append({"event": "police.alerted", "at": datetime.utcnow().isoformat(), "threat_level": payload.threat_level})
        session.timeline_json = json.dumps(timeline[-100:], ensure_ascii=True)
    db.commit()
    db.refresh(notification)

    broadcast_payload = {
        "notification_id": notification.notification_id,
        "incident_id": notification.incident_id,
        "session_id": notification.emergency_session_id,
        "user_id": notification.user_id,
        "threat_level": payload.threat_level,
        "priority_score": payload.priority_score,
        "cameras": payload.cameras,
        "message": notification.message,
        "at": notification.sent_at.isoformat() if notification.sent_at else None,
    }
    realtime_hub.publish_from_sync(POLICE_ALERT_EVENT, broadcast_payload)
    if notification.emergency_session_id:
        realtime_hub.publish_session_from_sync(notification.emergency_session_id, POLICE_ALERT_EVENT, broadcast_payload)
    return {"status": "alerted", "alert": broadcast_payload}


@router.get("/agents/cameras")
def agent_cameras(db: Session = Depends(get_db), _auth=Depends(get_service_or_user)):
    rows = db.scalars(select(CCTVCamera).order_by(CCTVCamera.camera_id)).all()
    return {"count": len(rows), "cameras": [camera_out(row) for row in rows]}
