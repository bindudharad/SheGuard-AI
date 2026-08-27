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
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    speed: Optional[float] = 0
    battery: Optional[int] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


class TrackingStart(BaseModel):
    user_id: int
    session_id: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    speed: Optional[float] = 0
    battery: Optional[int] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


class TrackingUpdate(BaseModel):
    session_id: str
    user_id: int
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    speed: Optional[float] = 0
    battery: Optional[int] = None
    accuracy: Optional[float] = None
    timestamp: Optional[datetime] = None


class BehaviorEventCreate(BaseModel):
    """New schema for behavior events (following, approaching, etc.)"""
    behavior_type: str  # following, approaching, chasing, fleeing, confrontation, isolation
    target_id: Optional[int] = None
    follower_id: Optional[int] = None
    score: float = Field(ge=0.0, le=100.0)
    duration_seconds: float = Field(ge=0.0)
    timestamp: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class IncidentCreate(BaseModel):
    user_id: Optional[int] = None
    incident_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    ai_summary: Optional[str] = None
    explanation: Optional[str] = None
    camera_id: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    frame_count: Optional[int] = None
    metadata_path: Optional[str] = None
    image_path: Optional[str] = None
    video_path: Optional[str] = None


class EvidenceUpload(BaseModel):
    incident_id: int
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    metadata_path: Optional[str] = None


class IncidentLinkUserRequest(BaseModel):
    incident_id: int
    user_id: int
    distance_meters: Optional[float] = None
    match_method: str = "manual"


class EmergencyStartRequest(BaseModel):
    user_id: int
    incident_id: Optional[int] = None
    session_id: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    trigger_source: str = "manual"


class NotificationSendRequest(BaseModel):
    user_id: Optional[int] = None
    incident_id: Optional[int] = None
    emergency_session_id: Optional[str] = None
    channels: list[str] = ["app", "websocket"]
    message: Optional[str] = None
    recipient: Optional[str] = None


class CameraCreate(BaseModel):
    camera_name: str
    ip_address: Optional[str] = None
    rtsp_url: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
