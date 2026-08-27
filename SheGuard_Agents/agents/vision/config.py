from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from pathlib import Path

class VisionSettings(BaseSettings):
    vision_enabled: bool = True

    video_source_type: str = "webcam"
    video_source: str = "0"

    yolo_model_path: str = "yolov8n.pt"
    yolo_confidence: float = 0.45
    yolo_iou: float = 0.45
    yolo_image_size: int = 640
    yolo_device: str = "auto"

    yolo_detection_interval: int = 5
    yolo_min_confidence_for_new_track: float = 0.5

    tracker_confidence_threshold: float = 0.3
    tracker_max_missed_frames: int = 10

    pose_enabled: bool = True
    pose_model_complexity: int = 1
    pose_min_detection_confidence: float = 0.45
    pose_min_tracking_confidence: float = 0.45

    staged_mediapipe_enabled: bool = True
    mediapipe_trigger_threshold: float = 0.5

    temporal_enabled: bool = True
    temporal_sequence_length: int = 16
    gru_model_path: str = "models/v2/sheguard_sequence_model.pt"
    gru_scaler_path: str = "models/v2/sequence_scaler.joblib"
    gru_label_encoder_path: str = "models/v2/sequence_label_encoder.joblib"

    staged_gru_enabled: bool = True
    gru_trigger_threshold: float = 0.4

    tracking_enabled: bool = True
    tracking_max_distance: float = 120.0
    tracking_stale_seconds: float = 1.5

    track_velocity_history_len: int = 30
    track_trajectory_history_len: int = 60

    optical_flow_enabled: bool = True
    optical_flow_trigger_threshold: float = 0.4
    optical_flow_interval: int = 3

    frame_skip: int = 1
    max_fps: int = 30

    metrics_enabled: bool = True
    metrics_log_interval: int = 100

    debug_visualization: bool = False
    simulation_mode: bool = False

    models_dir: str = "models"
    captures_dir: str = "captures"
    clips_dir: str = "clips"

    # Attack detection thresholds (used for suspicious track detection)
    attack_speed_threshold: float = 15.0
    attack_distance_threshold: float = 170.0

    class Config:
        env_prefix = "VISION_"
        env_file = ".env"
        extra = "ignore"

def get_vision_config() -> VisionSettings:
    return VisionSettings()
