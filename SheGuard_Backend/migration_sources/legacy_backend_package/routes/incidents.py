import base64
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import EvidenceUpload, IncidentCreate
from backend.database import get_db
from backend.models import Evidence, Incident, LiveLocation, User
from backend.services.telegram import format_alert_text, send_telegram_alert
from backend.services.threat import calculate_threat_score, threat_label
from backend.services.advanced_threat import assess_threat, explain_detection, threat_level
from backend.services.incident_memory import IncidentMemory
from backend.services.realtime import realtime_hub
from backend.services.auth import get_current_user


router = APIRouter(tags=["incidents"])
memory = IncidentMemory()
EVIDENCE_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "evidence" / "uploads"


def incident_out(row: Incident) -> dict:
    return {
        "incident_id": row.incident_id,
        "user_id": row.user_id,
        "incident_type": row.incident_type,
        "confidence": row.confidence,
        "threat_score": row.threat_score,
        "threat_level": row.threat_level or threat_label(row.threat_score),
        "kidnap_suspicion_score": row.kidnap_suspicion_score,
        "ai_summary": row.ai_summary,
        "ai_provider": row.ai_provider,
        "explanation": row.explanation,
        "camera_id": row.camera_id,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "created_at": row.created_at,
    }


def evidence_out(row: Evidence) -> dict:
    return {
        "evidence_id": row.evidence_id,
        "incident_id": row.incident_id,
        "image_path": row.image_path,
        "video_path": row.video_path,
        "cctv_source": row.cctv_source,
        "metadata_path": row.metadata_path,
        "pre_event_video_path": row.pre_event_video_path,
        "confidence": row.confidence,
        "threat_score": row.threat_score,
        "created_at": row.created_at,
    }


@router.post("/incident/create")
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    user = db.get(User, payload.user_id) if payload.user_id else None
    if payload.user_id and not user:
        raise HTTPException(status_code=404, detail="User not found")

    last_location = None
    if payload.user_id:
        last_location = db.scalars(
            select(LiveLocation).where(LiveLocation.user_id == payload.user_id).order_by(LiveLocation.timestamp.desc())
        ).first()

    latitude = payload.latitude if payload.latitude is not None else (last_location.latitude if last_location else None)
    longitude = payload.longitude if payload.longitude is not None else (last_location.longitude if last_location else None)
    speed = last_location.speed if last_location else None
    created_at = datetime.utcnow()
    score = payload.threat_score
    assessment = None
    if score is None:
        assessment = assess_threat(payload.incident_type, payload.confidence, motion_anomaly=1.0 if speed and speed >= 3.5 else 0.0, created_at=created_at)
        score = assessment.score
    else:
        assessment = assess_threat(payload.incident_type, payload.confidence, motion_anomaly=1.0 if speed and speed >= 3.5 else 0.0, created_at=created_at)

    incident = Incident(
        user_id=payload.user_id,
        incident_type=payload.incident_type,
        confidence=payload.confidence,
        threat_score=score,
        threat_level=payload.threat_level or threat_level(score),
        kidnap_suspicion_score=payload.kidnap_suspicion_score or assessment.kidnap_suspicion_score,
        ai_summary=payload.ai_summary or "Local AI detected a possible safety incident.",
        ai_provider=payload.ai_provider,
        explanation=payload.explanation or explain_detection(payload.incident_type, assessment),
        camera_id=payload.camera_id,
        latitude=latitude,
        longitude=longitude,
        created_at=created_at,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    evidence = Evidence(
        incident_id=incident.incident_id,
        image_path=payload.image_path,
        video_path=payload.video_path,
        cctv_source=payload.cctv_source,
        metadata_path=payload.metadata_path,
        pre_event_video_path=payload.pre_event_video_path,
        confidence=payload.confidence,
        threat_score=score,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    alert_result = {"enabled": False}
    if payload.send_alert and score >= 5:
        text = format_alert_text(
            user_name=user.full_name if user else "CCTV monitored area",
            event=incident.incident_type,
            confidence=incident.confidence,
            threat_label=threat_label(score),
            latitude=latitude,
            longitude=longitude,
            timestamp=incident.created_at.strftime("%Y-%m-%d %I:%M %p"),
            summary=incident.ai_summary,
        )
        alert_result = send_telegram_alert(text, payload.image_path, payload.video_path)

    response_payload = {"incident": incident_out(incident), "evidence": evidence_out(evidence), "telegram": alert_result}
    memory.remember(
        incident.incident_id,
        f"{incident.incident_type} {incident.threat_level} {incident.ai_summary or ''} {incident.explanation or ''}",
        {"camera_id": incident.camera_id, "latitude": latitude, "longitude": longitude, "threat_score": score},
    )
    realtime_hub.publish_from_sync("incident.created", response_payload)
    return response_payload


@router.get("/incident/history/{user_id}")
def incident_history(user_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(Incident).where(Incident.user_id == user_id).order_by(Incident.created_at.desc())).all()
    return {"count": len(rows), "incidents": [incident_out(row) for row in rows]}


@router.get("/incident/live")
def live_incidents(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(select(Incident).order_by(Incident.created_at.desc()).limit(limit)).all()
    return {"count": len(rows), "incidents": [incident_out(row) for row in rows]}


@router.get("/incident/search")
def search_incidents(q: str, limit: int = 5):
    matches = memory.search(q, limit=limit)
    return {
        "query": q,
        "count": len(matches),
        "matches": [
            {
                "incident_id": match.incident_id,
                "similarity": match.similarity,
                "summary": match.summary,
                "metadata": match.metadata,
            }
            for match in matches
        ],
    }


@router.get("/evidence/{incident_id}")
def evidence_for_incident(incident_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(Evidence).where(Evidence.incident_id == incident_id).order_by(Evidence.created_at.desc())).all()
    return {"count": len(rows), "evidence": [evidence_out(row) for row in rows]}


@router.get("/secure/evidence/{incident_id}")
def secure_evidence_for_incident(incident_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.user_id is not None and incident.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Evidence access denied")
    rows = db.scalars(select(Evidence).where(Evidence.incident_id == incident_id).order_by(Evidence.created_at.desc())).all()
    return {"count": len(rows), "evidence": [evidence_out(row) for row in rows]}


@router.post("/evidence/upload")
def upload_encrypted_evidence(payload: EvidenceUpload):
    EVIDENCE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(payload.filename).name
    target = EVIDENCE_UPLOAD_DIR / safe_name
    try:
        target.write_bytes(base64.b64decode(payload.content_base64))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid evidence payload") from exc
    metadata = {
        "session_id": payload.session_id,
        "evidence_type": payload.evidence_type,
        "filename": safe_name,
        "encrypted": payload.encrypted,
        "created_at": (payload.created_at or datetime.utcnow()).isoformat(),
    }
    metadata_path = target.with_suffix(target.suffix + ".json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"status": "stored", "path": str(target), "metadata_path": str(metadata_path)}
