from __future__ import annotations

import json
import logging
import os
import shutil
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Deque, Optional, Tuple

import cv2
import numpy as np

from app.services.media_storage import create_incident_folder, write_incident_metadata

logger = logging.getLogger("sheguard.evidence")


def normalize_bgr_frame(frame: Any) -> Optional[np.ndarray]:
    """Normalize a frame to BGR format for OpenCV."""
    if frame is None:
        return None
    if isinstance(frame, np.ndarray):
        if frame.ndim == 3 and frame.shape[2] == 3:
            return frame
        if frame.ndim == 2:
            return cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if frame.ndim == 3 and frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    return None


def write_video(frames: list[np.ndarray], output_path: str, fps: float = 20.0) -> Optional[str]:
    """Write a list of frames to an MP4 video file."""
    if not frames:
        return None
    try:
        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not writer.isOpened():
            logger.error("video_writer_failed", extra={"path": output_path})
            return None
        for frame in frames:
            writer.write(frame)
        writer.release()
        return output_path
    except Exception as exc:
        logger.error("video_write_error", extra={"error": str(exc)})
        return None


class RollingVideoBuffer:
    def __init__(self, pre_event_seconds: float = 10.0, fps: float = 20.0) -> None:
        self.fps = fps
        self.max_frames = max(1, int(pre_event_seconds * fps))
        self.frames: Deque[tuple[float, Any]] = deque(maxlen=self.max_frames)
        self.frame_size: Optional[Tuple[int, int]] = None

    def add(self, frame: Any, timestamp: float | None = None) -> None:
        valid_frame = normalize_bgr_frame(frame)
        if valid_frame is None:
            return
        timestamp = timestamp or time.time()
        logger.debug("recording_frame", extra={"buffer_size": len(self.frames) + 1})
        self.frames.append((timestamp, valid_frame.copy()))
        height, width = valid_frame.shape[:2]
        self.frame_size = (width, height)

    def pre_event_frames(self) -> list[Any]:
        return [frame.copy() for _, frame in self.frames]

    def save_pre_event_clip(self, output_path: str, fps: float | None = None) -> Optional[str]:
        if not self.frames or self.frame_size is None:
            return None
        return write_video([frame for _, frame in self.frames], output_path, fps or self.fps)

    def save_event_clip(
        self,
        output_path: str,
        post_event_frames: list[Any] | None = None,
        fps: float | None = None,
    ) -> Optional[str]:
        if self.frame_size is None:
            return None
        frames = self.pre_event_frames()
        frames.extend(frame.copy() for frame in (post_event_frames or []))
        return write_video(frames, output_path, fps or self.fps)


class EvidenceManager:
    def __init__(
        self,
        evidence_dir: str = "uploads/evidence",
        pre_event_seconds: float = 10.0,
        fps: float = 20.0,
        max_clips: int = 100,
    ) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.pre_event_seconds = pre_event_seconds
        self.fps = fps
        self.max_clips = max_clips
        self.buffer = RollingVideoBuffer(pre_event_seconds, fps)
        self.active_recordings: dict[str, RollingVideoBuffer] = {}

    def start_recording(self, session_id: str) -> None:
        logger.info("recording_started", extra={"session_id": session_id})
        self.active_recordings[session_id] = RollingVideoBuffer(self.pre_event_seconds, self.fps)

    def add_frame(self, session_id: str, frame: Any, timestamp: float | None = None) -> None:
        if session_id in self.active_recordings:
            self.active_recordings[session_id].add(frame, timestamp)

    def stop_recording(self, session_id: str, incident_id: str | None = None) -> Optional[str]:
        if session_id not in self.active_recordings:
            return None
        buffer = self.active_recordings.pop(session_id)
        output_path = str(self.evidence_dir / (session_id + ".mp4"))
        return buffer.save_pre_event_clip(output_path, self.fps)

    # Alias methods for test compatibility
    def record_frame(self, frame: Any) -> None:
        """Add a frame to the rolling buffer (for testing)."""
        self.buffer.add(frame)

    def save_detection_evidence(
        self,
        event_frame: Any,
        event_type: str,
        camera_id: str = "unknown",
        post_event_frames: list[Any] | None = None,
    ) -> dict:
        """Save detection evidence including image, video, and metadata."""
        import uuid
        incident_id = "incident_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + str(uuid.uuid4())[:8]
        incident_dir = self.evidence_dir / incident_id
        incident_dir.mkdir(parents=True, exist_ok=True)
        
        # Save event frame as image
        image_path = incident_dir / "frame_1.jpg"
        event_frame_normalized = normalize_bgr_frame(event_frame)
        if event_frame_normalized is not None:
            cv2.imwrite(str(image_path), event_frame_normalized)
        
        # Save pre-event + event + post-event as video
        video_path = incident_dir / "incident_video.mp4"
        self.buffer.save_event_clip(str(video_path), post_event_frames, self.fps)
        
        # Save metadata
        metadata_path = incident_dir / "metadata.json"
        metadata = {
            "incident_id": incident_id,
            "detection_type": event_type,
            "camera_id": camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "frame_count": len(self.buffer.frames) + len(post_event_frames or []),
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        
        return {
            "incident_id": incident_id,
            "incident_dir": str(incident_dir),
            "image_path": str(image_path),
            "video_path": str(video_path),
            "metadata_path": str(metadata_path),
        }
