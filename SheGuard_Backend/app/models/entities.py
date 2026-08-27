from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), default='user', nullable=False)
    profile_photo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    contacts = relationship('EmergencyContact', back_populates='user', cascade='all, delete-orphan')
    locations = relationship('LiveLocation', back_populates='user', cascade='all, delete-orphan')
    incidents = relationship('Incident', back_populates='user', cascade='all, delete-orphan', foreign_keys='Incident.user_id')
    tracking_sessions = relationship('TrackingSession', back_populates='user', cascade='all, delete-orphan')
    emergency_sessions = relationship('EmergencySession', back_populates='user', cascade='all, delete-orphan')


class EmergencyContact(Base):
    __tablename__ = 'emergency_contacts'

    contact_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String(80), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=False)

    user = relationship('User', back_populates='contacts')


class LiveLocation(Base):
    __tablename__ = 'live_locations'

    location_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship('User', back_populates='locations')


class TrackingSession(Base):
    __tablename__ = 'tracking_sessions'

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default='active', nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_battery: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_update_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    user = relationship('User', back_populates='tracking_sessions')


class Incident(Base):
    __tablename__ = 'incidents'

    incident_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.user_id'), nullable=True, index=True)
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    threat_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    threat_level: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    kidnap_suspicion_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='new', nullable=False, index=True)
    linked_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.user_id'), nullable=True, index=True)
    matching_distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    emergency_session_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Phase H new fields
    behavior_events_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    following_relationship: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk_reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    agent_timeline: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    x402_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    algorand_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    intelligence_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    user = relationship('User', back_populates='incidents', foreign_keys=[user_id])
    evidence = relationship('Evidence', back_populates='incident', cascade='all, delete-orphan')
    victim_links = relationship('IncidentVictimLink', back_populates='incident', cascade='all, delete-orphan')
    evidence_records = relationship('EvidenceRecord', back_populates='incident', cascade='all, delete-orphan')
    behavior_events = relationship('BehaviorEvent', back_populates='incident', cascade='all, delete-orphan')
    risk_events = relationship('RiskEvent', back_populates='incident', cascade='all, delete-orphan')
    x402_payments = relationship('X402Payment', back_populates='incident', cascade='all, delete-orphan')


class Evidence(Base):
    __tablename__ = 'evidence'

    evidence_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.incident_id'), nullable=False, index=True)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    cctv_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pre_event_video_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    threat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    incident = relationship('Incident', back_populates='evidence')


class IncidentVictimLink(Base):
    __tablename__ = 'incident_victim_links'

    link_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.incident_id'), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)
    emergency_session_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_method: Mapped[str] = mapped_column(String(50), default='gps_radius', nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    incident = relationship('Incident', back_populates='victim_links')
    user = relationship('User')


class EmergencySession(Base):
    __tablename__ = 'emergency_sessions'

    session_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.incident_id'), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.user_id'), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default='active', nullable=False, index=True)
    trigger_source: Mapped[str] = mapped_column(String(50), default='ai_cctv', nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_update_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    live_tracking_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship('User', back_populates='emergency_sessions')
    incident = relationship('Incident')
    notifications = relationship('EmergencyNotification', back_populates='emergency_session', cascade='all, delete-orphan')


class EmergencyNotification(Base):
    __tablename__ = 'emergency_notifications'

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey('incidents.incident_id'), nullable=True, index=True)
    emergency_session_id: Mapped[str | None] = mapped_column(ForeignKey('emergency_sessions.session_id'), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.user_id'), nullable=True, index=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey('emergency_contacts.contact_id'), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    recipient: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='queued', nullable=False, index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    emergency_session = relationship('EmergencySession', back_populates='notifications')
    incident = relationship('Incident')
    user = relationship('User')
    contact = relationship('EmergencyContact')


class EvidenceRecord(Base):
    __tablename__ = 'evidence_records'

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey('incidents.incident_id'), nullable=False, index=True)
    emergency_session_id: Mapped[str | None] = mapped_column(ForeignKey('emergency_sessions.session_id'), nullable=True, index=True)
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    incident = relationship('Incident', back_populates='evidence_records')
    emergency_session = relationship('EmergencySession')


class CCTVCamera(Base):
    __tablename__ = 'cctv_cameras'

    camera_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_name: Mapped[str] = mapped_column(String(150), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rtsp_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    online_status: Mapped[str] = mapped_column(String(30), default='unknown', nullable=False)