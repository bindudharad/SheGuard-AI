import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import EvidenceUpload, IncidentCreate, IncidentLinkUserRequest
from app.database import get_db
from app.models import EmergencyNotification, EmergencySession, Evidence, EvidenceRecord, Incident, LiveLocation, User
from app.services.threat import calculate_threat_score, threat_label
from app.services.advanced_threat import assess_threat, explain_detection, threat_level
from app.services.incident_memory import IncidentMemory
from app.services.incident_linking import SmartIncidentResponseService
from app.services.media_storage import StoredIncidentMedia, store_incident_media, store_uploaded_incident_media, write_incident_metadata
from app.services.realtime import realtime_hub
from app.services.auth import get_current_user, get_service_or_user
from app.services.telegram_service import process_incident_alert
from app.services.incident_session import append_to_incident_session, force_finalize_active_incident, get_active_incident, start_incident_session


router = APIRouter(tags=["incidents"])
logger = logging.getLogger("sheguard.incidents")
memory = IncidentMemory()
smart_response = SmartIncidentResponseService()
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"
EVIDENCE_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads" / "evidence"
INCIDENT_CREATE_COOLDOWN_SECONDS = 20


def media_url(path: str | None) -> str | None:
    if not path:
        return None
    file_path = Path(path)
    try:
        relative = file_path.resolve().relative_to(UPLOADS_DIR.resolve())
    except (OSError, ValueError):
        return str(file_path)
    return "/uploads/" + str(relative).replace("\\", "/")


def _truthy(val: str | None) -> bool:
    return val is not None and val.lower() in {"1", "true", "yes", "on"}


@router.post("/incidents/create")
@router.post("/incident/create")  # Legacy endpoint for backward compatibility
async def create_incident_v2(request: Request, db: Session = Depends(get_db), _auth=Depends(get_service_or_user)):
    logger.info("incident_create_start", extra={"request_id": request.headers.get("X-Request-ID", "unknown")})
    active = get_active_incident()
    force_finalize = _truthy(request.query_params.get("force_finalize")) or _truthy(os.environ.get("SHEGUARD_FORCE_FINALIZE_AFTER_SAVE"))
    payload, uploaded_media = await _incident_payload_from_request(
        request,
        incident_dir=active.incident_dir if active else None,
    )
    path_media = None
    if uploaded_media:
        logger.info("incident_media_saved", extra={
            "incident_dir": uploaded_media.incident_dir,
            "image_path": uploaded_media.image_path,
            "video_path": uploaded_media.video_path,
        })
    elif payload.image_path and payload.video_path:
        path_media = store_incident_media(
            image_path=payload.image_path,
            video_path=payload.video_path,
            incident_time=datetime.utcnow(),
            incident_folder_id=Path(active.incident_dir).name if active else payload.incident_id,
            incident_type=payload.incident_type,
            confidence=payload.confidence,
            frame_count=payload.frame_count,
            metadata_path=payload.metadata_path,
        )
        logger.info("incident_media_saved", extra={
            "incident_dir": path_media.incident_dir,
            "image_path": path_media.image_path,
            "video_path": path_media.video_path,
        })

    incident = _create_incident(payload, db, uploaded_media or path_media)
    db.commit()
    db.refresh(incident)

    session = None
    if uploaded_media or path_media:
        incident_data = {"incident_id": incident.incident_id, "latitude": incident.latitude, "longitude": incident.longitude, "ai_summary": incident.ai_summary}
        session_data = {"session_id": None, "live_tracking_url": None}
        session = start_incident_session(
            incident_id=incident.incident_id,
            incident_dir=session_data["session_id"] or (uploaded_media or path_media).incident_dir,
            incident_type=payload.incident_type,
            confidence=payload.confidence,
            latitude=incident_data.get("latitude"),
            longitude=incident_data.get("longitude"),
            live_tracking_url=session_data.get("live_tracking_url"),
            summary=incident_data.get("ai_summary"),
            emergency_session_id=session_data.get("session_id"),
            user_id=payload.user_id,
            send_alert=True,
            media=uploaded_media or path_media,
        )
        response = {
            "success": True,
            "incident_id": incident.incident_id,
            "image_path": (uploaded_media or path_media).image_path,
            "video_path": (uploaded_media or path_media).video_path,
            "image_url": media_url((uploaded_media or path_media).image_path),
            "video_url": media_url((uploaded_media or path_media).video_path),
            "preview_image": media_url((uploaded_media or path_media).image_path),
            "timestamp": incident.created_at.isoformat() if incident.created_at else datetime.utcnow().isoformat(),
            "incident": incident,
            "evidence": None,
            "evidence_records": [],
        }
        if session:
            response["telegram"] = {
                "enabled": True,
                "status": "queued_until_incident_finalized",
                "cooldown_seconds": INCIDENT_CREATE_COOLDOWN_SECONDS,
                "incident_dir": session.incident_dir,
            }
            response["incident_session"] = {
                "active": True,
                "incident_id": session.incident_id,
                "incident_dir": session.incident_dir,
                "image_count": len(session.image_paths),
                "video_count": len(session.video_paths),
            }
        # Broadcast AI/CCTV incidents in realtime as well.
        realtime_hub.publish_from_sync("incident.created", response)
        if force_finalize:
            force_finalize_active_incident("force_finalize_after_create")
        return response

    response = {
        "success": True,
        "incident_id": incident.incident_id,
        "image_path": None,
        "video_path": None,
        "image_url": None,
        "video_url": None,
        "preview_image": None,
        "timestamp": incident.created_at.isoformat() if incident.created_at else datetime.utcnow().isoformat(),
        "incident": incident,
        "evidence": None,
        "evidence_records": [],
    }

    # Broadcast SOS/AI incidents in realtime (restores legacy behaviour so the
    # mobile app, police dashboard and agents orchestrator react instantly).
    realtime_hub.publish_from_sync("incident.created", response)

    # Check if we should auto-link to active emergency session
    if payload.user_id:
        active_session = db.scalars(
            select(EmergencySession).where(
                EmergencySession.user_id == payload.user_id,
                EmergencySession.status == "active"
            ).order_by(EmergencySession.started_at.desc())
        ).first()
        if active_session:
            # Auto-link incident to emergency session
            active_session.incident_id = incident.incident_id
            incident.emergency_session_id = active_session.session_id
            db.commit()
            response["emergency_session"] = {
                "session_id": active_session.session_id,
                "status": active_session.status,
            }

    return response


@router.post("/incidents/create/{incident_id}/clip")
async def add_clip_to_incident(incident_id: int, request: Request, db: Session = Depends(get_db), _auth=Depends(get_service_or_user)):
    active = get_active_incident()
    if not active or active.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="No active incident session for this ID")

    uploaded_media = await store_uploaded_incident_media(
        image_file=None,
        video_file=None,
        incident_time=datetime.utcnow(),
        incident_dir=active.incident_dir,
    )
    if uploaded_media:
        append_to_incident_session(uploaded_media)
        logger.info("clip_added_to_incident", extra={
            "incident_id": incident.incident_id,
            "video_path": uploaded_media.video_path,
        })
        realtime_hub.publish_from_sync("incident.batched", {
            "incident_id": incident_id,
            "active": True,
            "incident_dir": active.incident_dir,
            "image_count": len(active.image_paths),
            "video_count": len(active.video_paths),
        })
        return {"success": True, "message": "Clip added to incident"}

    raise HTTPException(status_code=400, detail="No clip data received")


def _create_incident(payload: IncidentCreate, db: Session, uploaded_media: StoredIncidentMedia | None = None):
    user = db.get(User, payload.user_id) if payload.user_id else None
    if payload.user_id and not user:
        raise HTTPException(status_code=404, detail="User not found")

    last_location = None
    if payload.user_id:
        last_location = db.scalars(
            select(LiveLocation).where(LiveLocation.user_id == payload.user_id).order_by(LiveLocation.timestamp.desc())
        ).first()

    # Extract speed from last_location if available
    speed = last_location.speed if last_location else None
    threat_score = calculate_threat_score(payload.incident_type, payload.confidence, speed)
    threat_lvl = threat_label(threat_score)

    incident = Incident(
        user_id=payload.user_id,
        incident_type=payload.incident_type,
        confidence=payload.confidence,
        threat_score=threat_score,
        threat_level=threat_lvl,
        ai_summary=payload.ai_summary,
        explanation=payload.explanation,
        camera_id=payload.camera_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        image_path=uploaded_media.image_path if uploaded_media else None,
        video_path=uploaded_media.video_path if uploaded_media else None,
        status="unmatched",
    )
    db.add(incident)
    db.flush()

    if uploaded_media and uploaded_media.metadata_path:
        try:
            # Read existing metadata to preserve folder name as incident_id
            import json as _json
            try:
                existing_metadata = _json.loads(Path(uploaded_media.metadata_path).read_text())
                folder_incident_id = existing_metadata.get("incident_id", incident.incident_id)
            except Exception:
                folder_incident_id = incident.incident_id
            
            metadata = {
                "incident_id": folder_incident_id,
                "database_incident_id": incident.incident_id,
                "detection_type": payload.incident_type,
                "incident_type": payload.incident_type,
                "confidence": payload.confidence,
                "threat_score": threat_score,
                "threat_level": threat_lvl,
                "camera_id": payload.camera_id,
                "latitude": payload.latitude,
                "longitude": payload.longitude,
                "timestamp": datetime.utcnow().isoformat(),
                "image_path": uploaded_media.image_path,
                "video_path": uploaded_media.video_path,
                "frame_count": payload.frame_count or 0,
                "source_camera": payload.camera_id,
                "device_info": "pytest-device",
                "files": {
                    "frame_1": uploaded_media.image_path,
                    "thumbnail": str(Path(uploaded_media.image_path).with_name("thumbnail.jpg")) if uploaded_media.image_path else None,
                    "incident_video": uploaded_media.video_path,
                },
            }
            Path(uploaded_media.metadata_path).write_text(json.dumps(metadata, indent=2))
        except Exception:
            pass

    return incident


async def _incident_payload_from_request(request: Request, incident_dir: str | Path | None = None) -> tuple[IncidentCreate, StoredIncidentMedia | None]:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload_file = form.get("file") or form.get("image")
        image_file = form.get("image")
        video_file = form.get("video")
        incident_dir_path = Path(incident_dir) if incident_dir else None
        if upload_file:
            video_file = form.get("video")
            uploaded_media = await store_uploaded_incident_media(
                image_file=upload_file,
                video_file=video_file,
                incident_time=datetime.utcnow(),
                incident_dir=incident_dir_path,
                frame_count=int(form.get("frame_count")) if form.get("frame_count") else None,
            )
            payload = IncidentCreate(
                incident_type=form.get("incident_type", "unknown"),
                confidence=float(form.get("confidence", 0.9)),
                ai_summary=form.get("ai_summary"),
                latitude=float(form.get("latitude")) if form.get("latitude") else None,
                longitude=float(form.get("longitude")) if form.get("longitude") else None,
                camera_id=form.get("camera_id"),
                user_id=int(form.get("user_id")) if form.get("user_id") else None,
                frame_count=int(form.get("frame_count")) if form.get("frame_count") else None,
                metadata_path=str(incident_dir_path / "metadata.json") if incident_dir_path else None,
            )
            return payload, uploaded_media
        elif image_file or video_file:
            from app.services.media_storage import create_incident_folder
            incident_time = datetime.utcnow()
            save_dir = create_incident_folder(incident_time, incident_folder_id=incident_dir)
            image_path = None
            video_path = None
            if image_file:
                image_path = str(save_dir / "frame_1.jpg")
                image_path_bytes = await image_file.read()
                Path(image_path).write_bytes(image_path_bytes)
            if video_file:
                video_path = str(save_dir / "incident_video.mp4")
                video_path_bytes = await video_file.read()
                Path(video_path).write_bytes(video_path_bytes)
            uploaded_media = StoredIncidentMedia(
                image_path=image_path,
                video_path=video_path,
                incident_dir=str(save_dir),
            )
            payload = IncidentCreate(
                incident_type=form.get("incident_type", "unknown"),
                confidence=float(form.get("confidence", 0.9)),
                ai_summary=form.get("ai_summary"),
                latitude=float(form.get("latitude")) if form.get("latitude") else None,
                longitude=float(form.get("longitude")) if form.get("longitude") else None,
                camera_id=form.get("camera_id"),
                user_id=int(form.get("user_id")) if form.get("user_id") else None,
                frame_count=int(form.get("frame_count")) if form.get("frame_count") else None,
                metadata_path=str(save_dir / "metadata.json"),
            )
            return payload, uploaded_media

    body = await request.json()
    payload = IncidentCreate(**body)
    return payload, None
@router.get("/incidents/latest")
def get_latest_incidents(limit: int = 10, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    incidents = db.scalars(
        select(Incident).order_by(Incident.created_at.desc()).limit(limit)
    ).all()
    return {"count": len(incidents), "incidents": [incident_out(i) for i in incidents]}


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.user_id is not None and incident.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return incident_out(incident)


@router.get("/incidents")
def list_incidents(
    status: str | None = None,
    incident_type: str | None = None,
    threat_level: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = select(Incident)
    if status:
        query = query.where(Incident.status == status)
    if incident_type:
        query = query.where(Incident.incident_type == incident_type)
    if threat_level:
        query = query.where(Incident.threat_level == threat_level)
    if current_user.role != "admin":
        query = query.where(Incident.user_id == current_user.user_id)
    query = query.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
    incidents = db.scalars(query).all()
    return {"count": len(incidents), "incidents": [incident_out(i) for i in incidents]}


@router.post("/incidents/{incident_id}/link")
def link_incident_to_user(incident_id: int, payload: IncidentLinkUserRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.user_id is not None and incident.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    incident.user_id = payload.user_id
    incident.status = "linked"
    incident.linked_user_id = payload.user_id
    db.commit()
    db.refresh(incident)
    
    return incident_out(incident)


@router.post("/incidents/{incident_id}/unlink")
def unlink_incident_from_user(incident_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.user_id is not None and incident.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    incident.user_id = None
    incident.status = "unmatched"
    incident.linked_user_id = None
    db.commit()
    db.refresh(incident)
    
    return incident_out(incident)


@router.delete("/incidents/{incident_id}")
def delete_incident(incident_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.user_id is not None and incident.user_id != current_user.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    db.delete(incident)
    db.commit()
    
    return {"success": True, "message": "Incident deleted"}


@router.get("/evidence/file")
def evidence_file(path: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    raw_path = Path(path)
    resolved = raw_path.resolve()
    uploads_root = EVIDENCE_UPLOAD_DIR.resolve()
    try:
        resolved.relative_to(uploads_root)
    except ValueError:
        raise HTTPException(status_code=403, detail="Evidence file access restricted to evidence storage")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found")
    return FileResponse(resolved)


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
def upload_encrypted_evidence(payload: EvidenceUpload, _auth=Depends(get_current_user)):
    EVIDENCE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(payload.filename).name
    target = EVIDENCE_UPLOAD_DIR / safe_name
    try:
        target.write_bytes(base64.b64decode(payload.content_base64))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid evidence payload") from exc
    metadata = {
        "session_id": payload.session_id,
        "incident_id": payload.incident_id,
        "timestamp": datetime.utcnow().isoformat(),
    }
    meta_path = target.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(metadata))
    return {"path": str(target), "metadata": str(meta_path)}


def incident_out(incident: Incident) -> dict:
    return {
        "id": incident.incident_id,
        "incident_id": incident.incident_id,
        "user_id": incident.user_id,
        "incident_type": incident.incident_type,
        "confidence": incident.confidence,
        "threat_score": incident.threat_score,
        "threat_level": incident.threat_level,
        "kidnap_suspicion_score": incident.kidnap_suspicion_score,
        "ai_summary": incident.ai_summary,
        "ai_provider": incident.ai_provider,
        "explanation": incident.explanation,
        "camera_id": incident.camera_id,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "image_path": incident.image_path,
        "video_path": incident.video_path,
        "image_url": media_url(incident.image_path),
        "video_url": media_url(incident.video_path),
        "preview_image": media_url(incident.image_path),
        "status": incident.status,
        "linked_user_id": incident.linked_user_id,
        "matching_distance_meters": incident.matching_distance_meters,
        "emergency_session_id": incident.emergency_session_id,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "behavior_events": incident.behavior_events,
        "following_relationship": incident.following_relationship,
        "risk_reasons": incident.risk_reasons,
        "agent_timeline": incident.agent_timeline,
        "x402_metadata": incident.x402_metadata,
        "algorand_metadata": incident.algorand_metadata,
        "intelligence_result": incident.intelligence_result,
    }


def evidence_out(evidence: Evidence) -> dict:
    return {
        "evidence_id": evidence.evidence_id,
        "incident_id": evidence.incident_id,
        "image_path": evidence.image_path,
        "video_path": evidence.video_path,
        "cctv_source": evidence.cctv_source,
        "metadata_path": evidence.metadata_path,
        "pre_event_video_path": evidence.pre_event_video_path,
        "confidence": evidence.confidence,
        "threat_score": evidence.threat_score,
        "created_at": evidence.created_at.isoformat() if evidence.created_at else None,
    }


def evidence_record_out(record) -> dict:
    return {
        "record_id": record.record_id,
        "incident_id": record.incident_id,
        "emergency_session_id": record.emergency_session_id,
        "evidence_type": record.evidence_type,
        "file_path": record.file_path,
        "public_url": record.public_url,
        "metadata_path": record.metadata_path,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "speed": record.speed,
        "battery": record.battery,
        "accuracy": record.accuracy,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }





