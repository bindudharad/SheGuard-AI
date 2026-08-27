from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import EmergencyStartRequest
from app.database import get_db
from app.models import EmergencySession, Incident, User
from app.services.auth import get_current_user
from app.services.emergency_session_manager import EmergencySessionManager
from app.services.notification_manager import NotificationManager
from app.services.realtime import realtime_hub
import json
from datetime import datetime


router = APIRouter(tags=["emergency"])
sessions = EmergencySessionManager()
notifications = NotificationManager()


@router.post("/emergency/start")
def start_emergency(payload: EmergencyStartRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot start an emergency for another user")
    incident = db.get(Incident, payload.incident_id) if payload.incident_id else None
    if payload.incident_id and not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    session = sessions.start_session(
        db,
        user=user,
        incident=incident,
        session_id=payload.session_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        trigger_source=payload.trigger_source,
    )
    notifications.notify_contacts(db, user=user, incident=incident, session=session)
    db.commit()
    db.refresh(session)
    return {
        "status": "active",
        "session": sessions.session_payload(session, incident),
    }


@router.get("/emergency/session/{session_id}")
def get_emergency_session(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.get(EmergencySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
    incident = db.get(Incident, session.incident_id) if session.incident_id else None
    # Check access - user can only view their own sessions
    if session.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "session": sessions.session_payload(session, incident),
        "incident": incident,
    }


@router.post("/emergency/session/{session_id}/acknowledge")
def acknowledge_emergency(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.get(EmergencySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
    # In a real system, check if current_user is authorized police operator
    session.status = "acknowledged"
    timeline = sessions._timeline(session)
    timeline.append({"event": "emergency.acknowledged", "at": datetime.utcnow().isoformat(), "by": current_user.full_name})
    session.timeline_json = json.dumps(timeline, ensure_ascii=True)
    db.commit()
    db.refresh(session)
    
    # Publish realtime event
    incident = db.get(Incident, session.incident_id) if session.incident_id else None
    realtime_hub.publish_from_sync("emergency.acknowledged", sessions.session_payload(session, incident))
    realtime_hub.publish_session_from_sync(session_id, "emergency.acknowledged", sessions.session_payload(session, incident))
    
    return {
        "status": "acknowledged",
        "session": sessions.session_payload(session, incident),
    }


@router.post("/emergency/session/{session_id}/respond")
def respond_emergency(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.get(EmergencySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
    session.status = "responding"
    timeline = sessions._timeline(session)
    timeline.append({"event": "emergency.responding", "at": datetime.utcnow().isoformat(), "by": current_user.full_name})
    session.timeline_json = json.dumps(timeline, ensure_ascii=True)
    db.commit()
    db.refresh(session)
    
    # Publish realtime event
    incident = db.get(Incident, session.incident_id) if session.incident_id else None
    realtime_hub.publish_from_sync("emergency.responding", sessions.session_payload(session, incident))
    realtime_hub.publish_session_from_sync(session_id, "emergency.responding", sessions.session_payload(session, incident))
    
    return {
        "status": "responding",
        "session": sessions.session_payload(session, incident),
    }


@router.post("/emergency/session/{session_id}/resolve")
def resolve_emergency(session_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    session = db.get(EmergencySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
    session.status = "resolved"
    session.ended_at = datetime.utcnow()
    timeline = sessions._timeline(session)
    timeline.append({"event": "emergency.resolved", "at": datetime.utcnow().isoformat(), "by": current_user.full_name})
    session.timeline_json = json.dumps(timeline, ensure_ascii=True)
    db.commit()
    db.refresh(session)
    
    # Also update linked incident
    if session.incident_id:
        incident = db.get(Incident, session.incident_id)
        if incident:
            incident.status = "resolved"
            incident.isResolved = True
    
    # Publish realtime event
    incident = db.get(Incident, session.incident_id) if session.incident_id else None
    realtime_hub.publish_from_sync("emergency.resolved", sessions.session_payload(session, incident))
    realtime_hub.publish_session_from_sync(session_id, "emergency.resolved", sessions.session_payload(session, incident))
    
    return {
        "status": "resolved",
        "session": sessions.session_payload(session, incident),
    }
