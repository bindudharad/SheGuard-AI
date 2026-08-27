from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CCTVCamera, Evidence, Incident, IncidentVictimLink, LiveLocation, User
from app.services.emergency_config import settings
from app.services.emergency_session_manager import EmergencySessionManager
from app.services.evidence_linking import EvidenceLinkingService
from app.services.geo import GeoPoint, haversine_distance_meters, has_coordinates
from app.services.notification_manager import NotificationManager
from app.services.realtime import realtime_hub
from app.services.victim_matching import VictimMatchingEngine, VictimMatch


class SmartIncidentResponseService:
    def __init__(self) -> None:
        self.matcher = VictimMatchingEngine()
        self.sessions = EmergencySessionManager()
        self.notifications = NotificationManager()
        self.evidence = EvidenceLinkingService()

    def resolve_coordinates(self, db: Session, *, latitude: float | None, longitude: float | None, camera_id: str | None) -> tuple[float | None, float | None]:
        if has_coordinates(latitude, longitude):
            return latitude, longitude
        if not camera_id:
            return latitude, longitude
        camera = None
        if str(camera_id).isdigit():
            camera = db.get(CCTVCamera, int(camera_id))
        if not camera:
            camera = db.scalar(select(CCTVCamera).where(CCTVCamera.camera_name == str(camera_id)))
        if camera and has_coordinates(camera.latitude, camera.longitude):
            return camera.latitude, camera.longitude
        return latitude, longitude

    def recent_duplicate(self, db: Session, *, incident_type: str, camera_id: str | None, latitude: float | None, longitude: float | None) -> Incident | None:
        cutoff = datetime.utcnow() - timedelta(seconds=settings.incident_cooldown_seconds)
        candidates = db.scalars(
            select(Incident)
            .where(Incident.incident_type == incident_type)
            .where(Incident.created_at >= cutoff)
            .order_by(Incident.created_at.desc())
        ).all()
        for row in candidates:
            if camera_id and row.camera_id == camera_id:
                return row
            if has_coordinates(latitude, longitude) and has_coordinates(row.latitude, row.longitude):
                distance = haversine_distance_meters(GeoPoint(latitude, longitude), GeoPoint(row.latitude, row.longitude))
                if distance <= settings.incident_match_radius_meters:
                    return row
        return None

    def link_existing_incident(self, db: Session, *, incident: Incident, user: User, distance_meters: float | None = None, match_method: str = "manual") -> tuple[IncidentVictimLink, object]:
        latest = db.scalars(select(LiveLocation).where(LiveLocation.user_id == user.user_id).order_by(LiveLocation.timestamp.desc())).first()
        session = self.sessions.start_session(
            db,
            user=user,
            incident=incident,
            latitude=latest.latitude if latest else incident.latitude,
            longitude=latest.longitude if latest else incident.longitude,
            trigger_source=match_method,
        )
        link = IncidentVictimLink(
            incident_id=incident.incident_id,
            user_id=user.user_id,
            emergency_session_id=session.session_id,
            distance_meters=distance_meters,
            match_method=match_method,
            confidence=incident.confidence,
        )
        db.add(link)
        incident.linked_user_id = user.user_id
        incident.matching_distance_meters = distance_meters
        incident.emergency_session_id = session.session_id
        incident.status = "linked"
        realtime_hub.publish_from_sync("incident.linked", {"incident_id": incident.incident_id, "user_id": user.user_id, "session_id": session.session_id})
        return link, session

    def auto_link_and_start_response(self, db: Session, *, incident: Incident, evidence_payload: dict, explicit_user: User | None = None) -> dict:
        match: VictimMatch | None = None
        user = explicit_user
        if user is None and has_coordinates(incident.latitude, incident.longitude):
            match = self.matcher.find_nearest_user(db, incident.latitude, incident.longitude)
            user = match.user if match else None

        session = None
        link = None
        if user:
            link, session = self.link_existing_incident(
                db,
                incident=incident,
                user=user,
                distance_meters=match.distance_meters if match else None,
                match_method="gps_radius" if match else "explicit_user",
            )
            self.evidence.create_records_for_incident(db, incident, evidence_payload, session.session_id)
            self.notifications.notify_contacts(db, user=user, incident=incident, session=session)
        else:
            incident.status = "unmatched"
            self.evidence.create_records_for_incident(db, incident, evidence_payload, None)
            realtime_hub.publish_from_sync(
                "incident.unmatched",
                {"incident_id": incident.incident_id, "reason": "no_nearby_active_user_or_missing_gps"},
            )
        return {"match": match, "user": user, "session": session, "link": link}
