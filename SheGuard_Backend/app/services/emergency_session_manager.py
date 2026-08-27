from __future__ import annotations

import json
from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models import EmergencySession, Incident, TrackingSession, User
from app.services.emergency_config import settings
from app.services.realtime import realtime_hub
import logging

logger = logging.getLogger(__name__)


class EmergencySessionManager:
    def start_session(
        self,
        db: Session,
        *,
        user: User,
        incident: Incident | None = None,
        session_id: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        trigger_source: str = 'ai_cctv',
    ) -> EmergencySession:
        now = datetime.utcnow()
        session_id = session_id or f'sos-{uuid4().hex[:16]}'
        session = db.get(EmergencySession, session_id)
        if not session:
            session = EmergencySession(
                session_id=session_id,
                user_id=user.user_id,
                incident_id=incident.incident_id if incident else None,
                trigger_source=trigger_source,
                started_at=now,
            )
            db.add(session)
        session.status = 'active'
        session.last_latitude = latitude
        session.last_longitude = longitude
        session.last_update_at = now if latitude is not None and longitude is not None else session.last_update_at
        session.live_tracking_url = f'{settings.base_url}/track/{session.session_id}'
        timeline = self._timeline(session)
        timeline.append({'event': 'emergency.started', 'at': now.isoformat(), 'incident_id': incident.incident_id if incident else None})
        session.timeline_json = json.dumps(timeline, ensure_ascii=True)

        tracking = db.get(TrackingSession, session.session_id)
        if not tracking:
            tracking = TrackingSession(session_id=session.session_id, user_id=user.user_id, started_at=now)
            db.add(tracking)
        tracking.status = 'active'
        tracking.last_latitude = latitude
        tracking.last_longitude = longitude
        tracking.last_update_at = now if latitude is not None and longitude is not None else tracking.last_update_at

        if incident:
            incident.status = 'linked'
            incident.linked_user_id = user.user_id
            incident.emergency_session_id = session.session_id
        
        logger.info(f'Publishing emergency.started for session {session.session_id}')
        realtime_hub.publish_from_sync('emergency.started', self.session_payload(session, incident))
        realtime_hub.publish_session_from_sync(session.session_id, 'emergency.started', self.session_payload(session, incident))
        logger.info(f'Published emergency.started for session {session.session_id}')
        return session

    def session_payload(self, session: EmergencySession, incident: Incident | None = None) -> dict:
        return {
            'session_id': session.session_id,
            'incident_id': incident.incident_id if incident else session.incident_id,
            'user_id': session.user_id,
            'status': session.status,
            'live_tracking_url': session.live_tracking_url,
            'latitude': session.last_latitude,
            'longitude': session.last_longitude,
            'started_at': session.started_at,
        }

    @staticmethod
    def _timeline(session: EmergencySession) -> list[dict]:
        if not session.timeline_json:
            return []
        try:
            return json.loads(session.timeline_json)
        except json.JSONDecodeError:
            return []