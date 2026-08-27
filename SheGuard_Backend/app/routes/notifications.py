from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import NotificationSendRequest
from app.database import get_db
from app.models import EmergencySession, Incident, User
from app.services.auth import get_current_user
from app.services.notification_manager import NotificationManager


router = APIRouter(tags=["notifications"])
manager = NotificationManager()


def notification_out(row):
    return {
        "notification_id": row.notification_id,
        "incident_id": row.incident_id,
        "emergency_session_id": row.emergency_session_id,
        "user_id": row.user_id,
        "contact_id": row.contact_id,
        "channel": row.channel,
        "recipient": row.recipient,
        "status": row.status,
        "retry_count": row.retry_count,
        "message": row.message,
        "error": row.error,
        "created_at": row.created_at,
        "sent_at": row.sent_at,
    }


@router.post("/notifications/send")
def send_notification(payload: NotificationSendRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.get(User, payload.user_id) if payload.user_id else None
    incident = db.get(Incident, payload.incident_id) if payload.incident_id else None
    session = db.get(EmergencySession, payload.emergency_session_id) if payload.emergency_session_id else None
    if payload.user_id and not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.incident_id and not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if payload.emergency_session_id and not session:
        raise HTTPException(status_code=404, detail="Emergency session not found")
    rows = manager.send_custom(
        db,
        user=user,
        incident=incident,
        session=session,
        channels=payload.channels,
        message=payload.message,
        recipient=payload.recipient,
    )
    db.commit()
    for row in rows:
        db.refresh(row)
    return {"status": "queued", "notifications": [notification_out(row) for row in rows]}
