from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.database.session import SessionLocal
from app.models import EmergencyNotification, Incident
from app.services.media_storage import StoredIncidentMedia
from app.services.telegram_service import (
    format_emergency_message,
    send_location,
    send_message,
    send_photo,
    send_video,
    telegram_credentials,
    validate_video_before_telegram,
)


INCIDENT_SESSION_TIMEOUT_SECONDS = 20


@dataclass
class IncidentSession:
    incident_id: int
    incident_dir: str
    incident_type: str
    confidence: float
    started_at: datetime
    last_activity: datetime
    latitude: float | None = None
    longitude: float | None = None
    live_tracking_url: str | None = None
    summary: str | None = None
    emergency_session_id: str | None = None
    user_id: int | None = None
    send_alert: bool = True
    image_paths: list[str] = field(default_factory=list)
    video_paths: list[str] = field(default_factory=list)
    metadata_path: str | None = None
    timer: threading.Timer | None = field(default=None, repr=False)


active_incident: IncidentSession | None = None
incident_start_time: datetime | None = None
incident_last_activity: datetime | None = None
_lock = threading.RLock()
_watchdog_started = False


def _ts() -> str:
    return datetime.utcnow().isoformat()


def get_active_incident() -> IncidentSession | None:
    with _lock:
        if not active_incident:
            return None
        if datetime.utcnow() - active_incident.last_activity > timedelta(seconds=INCIDENT_SESSION_TIMEOUT_SECONDS):
            print("STEP 4 COOLDOWN CHECK", _ts())
            print("[INCIDENT] Active session expired at route entry; finalizing before new session")
            session = active_incident
            _clear_active_unlocked()
            threading.Thread(target=_finalize_session_safely, args=(session,), daemon=True).start()
            return None
        return active_incident


def start_incident_session(
    *,
    incident_id: int,
    incident_dir: str,
    incident_type: str,
    confidence: float,
    latitude: float | None,
    longitude: float | None,
    live_tracking_url: str | None,
    summary: str | None,
    emergency_session_id: str | None,
    user_id: int | None,
    send_alert: bool,
    media: StoredIncidentMedia,
) -> IncidentSession:
    global active_incident, incident_start_time, incident_last_activity
    now = datetime.utcnow()
    with _lock:
        active_incident = IncidentSession(
            incident_id=incident_id,
            incident_dir=incident_dir,
            incident_type=incident_type,
            confidence=confidence,
            started_at=now,
            last_activity=now,
            latitude=latitude,
            longitude=longitude,
            live_tracking_url=live_tracking_url,
            summary=summary,
            emergency_session_id=emergency_session_id,
            user_id=user_id,
            send_alert=send_alert,
            metadata_path=media.metadata_path,
        )
        incident_start_time = now
        incident_last_activity = now
        _add_media_unlocked(active_incident, media)
        print("STEP 2 INCIDENT CREATED", _ts())
        print("[INCIDENT] Created")
        print("[INCIDENT] Active assigned")
        print("ACTIVE INCIDENT CREATED:", active_incident)
        print("UPDATED INCIDENT ACTIVITY")
        print("[INCIDENT] Folder:", incident_dir)
        _schedule_finalize_unlocked(active_incident)
        return active_incident


def append_to_incident_session(media: StoredIncidentMedia) -> IncidentSession | None:
    global incident_last_activity
    with _lock:
        if not active_incident:
            return None
        active_incident.last_activity = datetime.utcnow()
        incident_last_activity = active_incident.last_activity
        _add_media_unlocked(active_incident, media)
        print("STEP 1 DETECTION", _ts())
        print("[INCIDENT] Detection added")
        print("[INCIDENT] Activity updated")
        print("UPDATED INCIDENT ACTIVITY")
        print("[INCIDENT] Folder:", active_incident.incident_dir)
        print("clip added:", media.video_path)
        print("frame added:", media.image_path)
        _schedule_finalize_unlocked(active_incident)
        return active_incident


def _add_media_unlocked(session: IncidentSession, media: StoredIncidentMedia) -> None:
    if media.image_path and media.image_path not in session.image_paths:
        session.image_paths.append(media.image_path)
    if media.video_path and media.video_path not in session.video_paths:
        session.video_paths.append(media.video_path)
    if media.metadata_path:
        session.metadata_path = media.metadata_path


def _schedule_finalize_unlocked(session: IncidentSession) -> None:
    if session.timer:
        session.timer.cancel()
    timer = threading.Timer(INCIDENT_SESSION_TIMEOUT_SECONDS, _finalize_if_quiet, args=(session.incident_id,))
    timer.daemon = True
    session.timer = timer
    timer.start()


def _finalize_if_quiet(incident_id: int) -> None:
    with _lock:
        session = active_incident
        if not session or session.incident_id != incident_id:
            return
        quiet_for = datetime.utcnow() - session.last_activity
        if quiet_for < timedelta(seconds=INCIDENT_SESSION_TIMEOUT_SECONDS):
            _schedule_finalize_unlocked(session)
            return
        _clear_active_unlocked()

    print("[INCIDENT] Cooldown reached")
    _finalize_session_safely(session)


def start_incident_watchdog() -> None:
    global _watchdog_started
    with _lock:
        if _watchdog_started:
            return
        _watchdog_started = True
    thread = threading.Thread(target=_watchdog_loop, name="sheguard-incident-watchdog", daemon=True)
    thread.start()
    print("[INCIDENT] Watchdog started")


def force_finalize_active_incident(reason: str = "manual") -> bool:
    with _lock:
        if not active_incident:
            print("[INCIDENT] Force finalize requested but no active incident exists")
            return False
        session = active_incident
        print("[INCIDENT] Force finalizing active incident:", reason)
        _clear_active_unlocked()
    _finalize_session_safely(session)
    return True


def _watchdog_loop() -> None:
    while True:
        try:
            time.sleep(1)
            session_to_finalize: IncidentSession | None = None
            with _lock:
                session = active_incident
                now = datetime.utcnow()
                print("ACTIVE INCIDENT:", session)
                print("LAST ACTIVITY:", incident_last_activity)
                print("TIME SINCE LAST:", (now - incident_last_activity) if incident_last_activity else None)
                print("STEP 4 COOLDOWN CHECK", _ts())
                if session and now - session.last_activity > timedelta(seconds=INCIDENT_SESSION_TIMEOUT_SECONDS):
                    print("[INCIDENT] Cooldown reached")
                    session_to_finalize = session
                    _clear_active_unlocked()
            if session_to_finalize:
                _finalize_session_safely(session_to_finalize)
        except Exception as exc:
            print("WATCHDOG CRASH:", exc)


def _finalize_session_safely(session: IncidentSession) -> None:
    try:
        print("STEP 5 FINALIZING", _ts())
        print("[INCIDENT] Finalizing")
        print("[INCIDENT] Folder:", session.incident_dir)
        result = finalize_incident_session(session)
        print("incident finalized:", session.incident_id, result)
    except Exception as exc:
        print("TELEGRAM ERROR:", str(exc))
        print("[TELEGRAM] Failed")


def _clear_active_unlocked() -> None:
    global active_incident, incident_start_time, incident_last_activity
    if active_incident and active_incident.timer:
        active_incident.timer.cancel()
    active_incident = None
    incident_start_time = None
    incident_last_activity = None
    print("[INCIDENT] Reset complete")


def finalize_incident_session(session: IncidentSession) -> dict[str, Any]:
    image_paths = _existing_paths(session.image_paths + [str(path) for path in Path(session.incident_dir).glob("*.jpg")])
    video_paths = _existing_paths(session.video_paths + [str(path) for path in Path(session.incident_dir).glob("*.mp4")])
    print("sending telegram:", session.incident_id)
    print("folder path:", session.incident_dir)
    print("file count:", len(image_paths) + len(video_paths))
    print("jpg count:", len(image_paths))
    print("mp4 count:", len(video_paths))
    print("session images:", image_paths)
    print("session videos:", video_paths)

    telegram_result = _send_session_telegram(session, image_paths=image_paths, video_paths=video_paths) if session.send_alert else {
        "enabled": False,
        "reason": "send_alert_false",
    }
    _write_session_metadata(session, image_paths=image_paths, video_paths=video_paths, telegram_status=telegram_result)
    _store_notification(session, telegram_result)
    return telegram_result


def _send_session_telegram(session: IncidentSession, *, image_paths: list[str], video_paths: list[str]) -> dict[str, Any]:
    token, chat_id = telegram_credentials()
    print("STEP 6 CALLING TELEGRAM", _ts())
    print("CALLING send_telegram_alert")
    print("ENTERED TELEGRAM FUNCTION")
    print("CALLING TELEGRAM ALERT")
    print("BOT TOKEN:", _mask_secret(token))
    print("CHAT_ID:", chat_id or "missing")
    print("[TELEGRAM] Sending")
    print("[TELEGRAM] Sending alert")
    timestamp = session.started_at.strftime("%I:%M %p")
    text = format_emergency_message(
        incident_type=session.incident_type,
        confidence=session.confidence,
        timestamp=timestamp,
        latitude=session.latitude,
        longitude=session.longitude,
        live_tracking_url=session.live_tracking_url,
        summary=_session_summary(session, image_paths, video_paths),
        image_attached=bool(image_paths),
        video_attached=bool(video_paths),
    )
    result: dict[str, Any] = {
        "enabled": True,
        "message_sent": False,
        "location_sent": False,
        "photo_sent": False,
        "video_sent": False,
        "photo_count": 0,
        "video_count": 0,
        "errors": [],
        "responses": {},
    }

    try:
        test_message = send_message("TEST ALERT FROM FINALIZER")
        result["responses"]["finalizerTestMessage"] = test_message
        if not test_message.get("ok"):
            print("[TELEGRAM] Failed")
            result["errors"].append(test_message.get("error", "finalizer_test_failed"))

        message = send_message(text)
        result["message_sent"] = message.get("ok", False)
        result["responses"]["sendMessage"] = message
        if not message.get("ok"):
            print("[TELEGRAM] Failed")
            result["errors"].append(message.get("error", "message_failed"))
        else:
            print("[TELEGRAM] Success")
    except Exception as exc:
        print("TELEGRAM ERROR:", str(exc))
        print("[TELEGRAM] Failed")
        result["errors"].append(str(exc))

    if session.latitude is not None and session.longitude is not None:
        try:
            print("[TELEGRAM] Sending location")
            location = send_location(session.latitude, session.longitude)
            result["location_sent"] = location.get("ok", False)
            result["responses"]["sendLocation"] = location
            if not location.get("ok"):
                print("[TELEGRAM] Failed")
                result["errors"].append(location.get("error", "location_failed"))
            else:
                print("[TELEGRAM] Success")
        except Exception as exc:
            print("TELEGRAM ERROR:", str(exc))
            print("[TELEGRAM] Failed")
            result["errors"].append(str(exc))

    for image_path in image_paths:
        try:
            print("[TELEGRAM] Sending image")
            print("telegram photo upload started:", os.path.abspath(image_path))
            photo = send_photo(image_path)
            result["responses"].setdefault("sendPhoto", []).append(photo)
            if photo.get("ok"):
                result["photo_sent"] = True
                result["photo_count"] += 1
                print("telegram photo upload success:", os.path.abspath(image_path))
                print("[TELEGRAM] Success")
            else:
                error = photo.get("error", "photo_failed")
                print("telegram photo upload failure:", error)
                print("[TELEGRAM] Failed")
                result["errors"].append(error)
        except Exception as exc:
            print("TELEGRAM ERROR:", str(exc))
            print("[TELEGRAM] Failed")
            result["errors"].append(str(exc))

    for video_path in video_paths:
        try:
            absolute_video = os.path.abspath(video_path)
            validation_error = validate_video_before_telegram(absolute_video)
            if validation_error:
                print("telegram upload failure:", validation_error)
                print("[TELEGRAM] Failed")
                result["errors"].append(validation_error)
                continue
            print("[TELEGRAM] Sending video")
            print("telegram upload started:", absolute_video)
            video = send_video(absolute_video)
            result["responses"].setdefault("sendVideo", []).append(video)
            if video.get("ok"):
                result["video_sent"] = True
                result["video_count"] += 1
                print("telegram upload success:", absolute_video)
                print("[TELEGRAM] Success")
            else:
                error = video.get("error", "video_failed")
                print("telegram upload failure:", error)
                print("[TELEGRAM] Failed")
                result["errors"].append(error)
        except Exception as exc:
            print("TELEGRAM ERROR:", str(exc))
            print("[TELEGRAM] Failed")
            result["errors"].append(str(exc))

    print("STEP 7 TELEGRAM COMPLETE", _ts())
    return result


def _session_summary(session: IncidentSession, image_paths: list[str], video_paths: list[str]) -> str:
    base = session.summary or "Incident recording finished. Evidence batch is attached."
    return f"{base} Images: {len(image_paths)}. Videos: {len(video_paths)}."


def _existing_paths(paths: list[str]) -> list[str]:
    existing: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path)
        if path.exists() and path.is_file():
            resolved = str(path.resolve())
            if resolved not in seen:
                existing.append(resolved)
                seen.add(resolved)
        else:
            print("missing session media skipped:", raw_path)
    return existing


def _mask_secret(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _write_session_metadata(
    session: IncidentSession,
    *,
    image_paths: list[str],
    video_paths: list[str],
    telegram_status: dict[str, Any],
) -> None:
    metadata_path = Path(session.metadata_path) if session.metadata_path else Path(session.incident_dir) / "metadata.json"
    payload: dict[str, Any] = {}
    if metadata_path.exists():
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    payload.update(
        {
            "incident_id": Path(session.incident_dir).name,
            "database_incident_id": session.incident_id,
            "detection_type": session.incident_type,
            "confidence": session.confidence,
            "timestamp": session.started_at.isoformat(),
            "session_finalized_at": datetime.utcnow().isoformat(),
            "video_path": video_paths[0] if video_paths else None,
            "image_path": image_paths[0] if image_paths else None,
            "files": {
                "frames": image_paths,
                "videos": video_paths,
                "thumbnail": str(Path(session.incident_dir) / "thumbnail.jpg"),
            },
            "telegram_message_status": telegram_status,
        }
    )
    metadata_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _store_notification(session: IncidentSession, telegram_result: dict[str, Any]) -> None:
    db = SessionLocal()
    try:
        incident = db.get(Incident, session.incident_id)
        if incident:
            incident.status = "alert_sent" if telegram_result.get("video_sent") or telegram_result.get("message_sent") else incident.status
        db.add(
            EmergencyNotification(
                incident_id=session.incident_id,
                emergency_session_id=session.emergency_session_id,
                user_id=session.user_id,
                channel="telegram",
                recipient=os.environ.get("PARENT_CHAT_ID") or os.environ.get("CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID"),
                status="sent" if telegram_result.get("message_sent") else "failed",
                message="Telegram emergency evidence batch",
                error="; ".join(telegram_result.get("errors") or []) or None,
                sent_at=datetime.utcnow() if telegram_result.get("message_sent") else None,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        print("telegram notification record failed:", str(exc))
    finally:
        db.close()
