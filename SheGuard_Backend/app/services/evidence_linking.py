from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import EvidenceRecord, Incident
from app.services.emergency_config import settings


def evidence_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"{settings.base_url}/evidence/file?path={path}"


class EvidenceLinkingService:
    def create_records_for_incident(self, db: Session, incident: Incident, evidence_payload: dict, session_id: str | None = None) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for evidence_type, key in [
            ("snapshot", "image_path"),
            ("clip", "video_path"),
            ("pre_event_clip", "pre_event_video_path"),
            ("metadata", "metadata_path"),
        ]:
            path = evidence_payload.get(key)
            if not path:
                continue
            record = EvidenceRecord(
                incident_id=incident.incident_id,
                emergency_session_id=session_id,
                evidence_type=evidence_type,
                file_path=path,
                public_url=evidence_url(path),
                metadata_path=evidence_payload.get("metadata_path"),
                latitude=incident.latitude,
                longitude=incident.longitude,
                captured_at=incident.created_at or datetime.utcnow(),
            )
            db.add(record)
            records.append(record)
        return records
