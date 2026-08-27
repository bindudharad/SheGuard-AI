from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    full_name: str
    phone_number: str
    password: str = Field(min_length=6)
    profile_photo: Optional[str] = None


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class UserOut(BaseModel):
    user_id: int
    full_name: str
    phone_number: str
    profile_photo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ContactCreate(BaseModel):
    user_id: int
    relation: str
    contact_name: str
    phone_number: str


class LocationUpdate(BaseModel):
    user_id: int
    session_id: Optional[str] = None
    latitude: float
    longitude: float
    speed: Optional[float] = 0
    battery: Optional[int] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


class TrackingStart(BaseModel):
    user_id: int
    session_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    speed: Optional[float] = 0
    battery: Optional[int] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


class TrackingUpdate(BaseModel):
    session_id: str
    user_id: int
    latitude: float
    longitude: float
    speed: Optional[float] = 0
    battery: Optional[int] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


class IncidentCreate(BaseModel):
    user_id: Optional[int] = None
    incident_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    threat_score: Optional[int] = None
    threat_level: Optional[str] = None
    kidnap_suspicion_score: Optional[int] = None
    ai_summary: Optional[str] = None
    ai_provider: Optional[str] = None
    explanation: Optional[str] = None
    camera_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata_path: Optional[str] = None
    pre_event_video_path: Optional[str] = None
    cctv_source: Optional[str] = None
    send_alert: bool = True


class CameraCreate(BaseModel):
    camera_name: str
    ip_address: Optional[str] = None
    rtsp_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    online_status: str = "online"


class EvidenceUpload(BaseModel):
    session_id: str
    evidence_type: str
    filename: str
    content_base64: str
    encrypted: bool = True
    created_at: Optional[datetime] = None
