from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class VideoSourceType(str, Enum):
    WEBCAM = "webcam"
    FILE = "file"
    RTSP = "rtsp"
    DROIDCAM = "droidcam"


class DetectionClass(str, Enum):
    PERSON = "person"


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
    
    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def center(self) -> tuple:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    def to_dict(self) -> Dict[str, int]:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2, "width": self.width, "height": self.height}


@dataclass
class Detection:
    track_id: Optional[int] = None
    class_id: int = 0
    class_name: str = "person"
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox.to_dict() if self.bbox else None,
        }


@dataclass
class PoseLandmark:
    x: float
    y: float
    visibility: float
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "visibility": self.visibility}


@dataclass
class PoseData:
    track_id: int
    landmarks: Dict[str, PoseLandmark] = field(default_factory=dict)
    keypoints: List[tuple] = field(default_factory=list)
    head: Optional[tuple] = None
    hip: Optional[tuple] = None
    shoulder: Optional[tuple] = None
    visible: bool = False
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "landmarks": {k: v.to_dict() for k, v in self.landmarks.items()},
            "keypoints": self.keypoints,
            "head": self.head,
            "hip": self.hip,
            "shoulder": self.shoulder,
            "visible": self.visible,
            "confidence": self.confidence,
        }


@dataclass
class TrackingData:
    track_id: int
    bbox: BoundingBox
    center: tuple
    speed: float
    direction: Optional[str] = None
    distance_travelled: float = 0.0
    presence_duration: float = 0.0
    pose: Optional[PoseData] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "bbox": self.bbox.to_dict(),
            "center": self.center,
            "speed": self.speed,
            "direction": self.direction,
            "distance_travelled": self.distance_travelled,
            "presence_duration": self.presence_duration,
            "pose": self.pose.to_dict() if self.pose else None,
        }


@dataclass
class InteractionData:
    detected: bool = False
    confidence: float = 0.0
    participants: List[int] = field(default_factory=list)
    duration_seconds: float = 0.0
    distance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "confidence": self.confidence,
            "participants": self.participants,
            "duration_seconds": self.duration_seconds,
            "distance": self.distance,
        }


@dataclass
class ActivityData:
    label: str = "unknown"
    confidence: float = 0.0
    temporal_confidence: float = 0.0
    sequence_length: int = 0
    model_status: str = "NOT_READY"
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "confidence": self.confidence,
            "temporal_confidence": self.temporal_confidence,
            "sequence_length": self.sequence_length,
            "model_status": self.model_status,
            "evidence": self.evidence,
        }


@dataclass
class TemporalData:
    ready: bool = False
    confidence: float = 0.0
    sequence_length: int = 0
    frames_buffered: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ready": self.ready,
            "confidence": self.confidence,
            "sequence_length": self.sequence_length,
            "frames_buffered": self.frames_buffered,
        }


@dataclass
class VisionConfig:
    enabled: bool = True
    video_source_type: VideoSourceType = VideoSourceType.WEBCAM
    video_source: str = "0"
    yolo_model_path: str = "yolov8n.pt"
    yolo_confidence: float = 0.45
    yolo_iou: float = 0.45
    yolo_image_size: int = 640
    yolo_device: str = "auto"
    pose_enabled: bool = True
    temporal_enabled: bool = True
    temporal_sequence_length: int = 16
    tracking_enabled: bool = True
    tracking_max_distance: float = 120.0
    tracking_stale_seconds: float = 1.5
    tracker_confidence_threshold: float = 0.5
    tracker_max_missed_frames: int = 30
    yolo_detection_interval: int = 5
    yolo_min_confidence_for_new_track: float = 0.5
    frame_skip: int = 1
    max_fps: int = 30
    debug_visualization: bool = False
    simulation_mode: bool = False


@dataclass
class VisionOutput:
    agent: str = "vision_agent"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    frame_id: int = 0
    source: str = ""
    persons_detected: int = 0
    detections: List[Detection] = field(default_factory=list)
    tracking: List[TrackingData] = field(default_factory=list)
    pose: List[PoseData] = field(default_factory=list)
    interaction: InteractionData = field(default_factory=InteractionData)
    activity: ActivityData = field(default_factory=ActivityData)
    temporal: TemporalData = field(default_factory=TemporalData)
    visual_risk_signal: float = 0.0
    evidence: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    simulation: bool = False
    
    # New fields for Phase B/C
    following: List[Dict[str, Any]] = field(default_factory=list)
    behaviors: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent,
            "timestamp": self.timestamp,
            "frame_id": self.frame_id,
            "source": self.source,
            "persons_detected": self.persons_detected,
            "detections": [d.to_dict() for d in self.detections],
            "tracking": [t.to_dict() for t in self.tracking],
            "pose": [p.to_dict() for p in self.pose],
            "interaction": self.interaction.to_dict(),
            "activity": self.activity.to_dict(),
            "temporal": self.temporal.to_dict(),
            "visual_risk_signal": self.visual_risk_signal,
            "evidence": self.evidence,
            "processing_time_ms": self.processing_time_ms,
            "simulation": self.simulation,
            "following": self.following,
            "behaviors": self.behaviors,
        }
