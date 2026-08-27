from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmergencyContact, EmergencyNotification, EmergencySession, Incident, User
from app.services.emergency_config import settings
from app.services.realtime import realtime_hub


class NotificationManager:
    def build_message(self, *, user: User, incident: Incident | None, session: EmergencySession | None, contact_name: str | None = None) -> str:
        event = incident.incident_type if incident else "emergency"
        confidence = f"{incident.confidence:.0%}" if incident and incident.confidence is not None else "unknown"
        tracking_url = session.live_tracking_url if session else None
        camera = incident.camera_id if incident else None
        location = ""
        if incident and incident.latitude is not None and incident.longitude is not None:
            location = f"\nCamera GPS: {incident.latitude:.6f},{incident.longitude:.6f}"
        greeting = f"Hi {contact_name}," if contact_name else "Emergency alert:"
        return (
            f"{greeting}\n"
            f"{user.full_name} may need help. Event: {event}. Confidence: {confidence}."
            f"{location}\n"
            f"Live tracking: {tracking_url or 'not available yet'}\n"
            f"Time: {(incident.created_at if incident else datetime.utcnow()).isoformat()}"
        )

    def notify_contacts(self, db: Session, *, user: User, incident: Incident | None, session: EmergencySession | None, channels: list[str] | None = None) -> list[EmergencyNotification]:
        channels = channels or ["app", "websocket", "sms", "whatsapp"]
        contacts = db.scalars(select(EmergencyContact).where(EmergencyContact.user_id == user.user_id)).all()
        notifications: list[EmergencyNotification] = []
        for contact in contacts or [None]:
            for channel in channels:
                if self._recent_duplicate(db, session.session_id if session else None, contact.contact_id if contact else None, channel):
                    continue
                message = self.build_message(
                    user=user,
                    incident=incident,
                    session=session,
                    contact_name=contact.contact_name if contact else None,
                )
                notification = EmergencyNotification(
                    incident_id=incident.incident_id if incident else None,
                    emergency_session_id=session.session_id if session else None,
                    user_id=user.user_id,
                    contact_id=contact.contact_id if contact else None,
                    channel=channel,
                    recipient=contact.phone_number if contact else user.phone_number,
                    status="sent" if channel in {"app", "websocket"} else "queued",
                    retry_count=0,
                    message=message,
                    sent_at=datetime.utcnow() if channel in {"app", "websocket"} else None,
                )
                db.add(notification)
                notifications.append(notification)
        realtime_hub.publish_from_sync(
            "emergency.notifications",
            {
                "user_id": user.user_id,
                "incident_id": incident.incident_id if incident else None,
                "session_id": session.session_id if session else None,
                "count": len(notifications),
            },
        )
        return notifications

    def send_custom(self, db: Session, *, user: User | None, incident: Incident | None, session: EmergencySession | None, channels: list[str], message: str | None, recipient: str | None) -> list[EmergencyNotification]:
        rows: list[EmergencyNotification] = []
        for channel in channels:
            notification = EmergencyNotification(
                incident_id=incident.incident_id if incident else None,
                emergency_session_id=session.session_id if session else None,
                user_id=user.user_id if user else None,
                channel=channel,
                recipient=recipient or (user.phone_number if user else None),
                status="sent" if channel in {"app", "websocket"} else "queued",
                message=message or "SheGuard emergency notification.",
                sent_at=datetime.utcnow() if channel in {"app", "websocket"} else None,
            )
            db.add(notification)
            rows.append(notification)
        realtime_hub.publish_from_sync("notification.sent", {"count": len(rows), "channels": channels})
        return rows

    def _recent_duplicate(self, db: Session, session_id: str | None, contact_id: int | None, channel: str) -> bool:
        if not session_id:
            return False
        cutoff = datetime.utcnow() - timedelta(seconds=settings.notification_cooldown_seconds)
        existing = db.scalar(
            select(EmergencyNotification)
            .where(EmergencyNotification.emergency_session_id == session_id)
            .where(EmergencyNotification.channel == channel)
            .where(EmergencyNotification.contact_id == contact_id)
            .where(EmergencyNotification.created_at >= cutoff)
        )
        return existing is not None
