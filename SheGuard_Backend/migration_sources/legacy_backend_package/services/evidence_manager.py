from __future__ import annotations

import json
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Deque, Optional, Tuple

import cv2


class RollingVideoBuffer:
    def __init__(self, pre_event_seconds: float = 30.0, fps: float = 20.0) -> None:
        self.fps = fps
        self.max_frames = max(1, int(pre_event_seconds * fps))
        self.frames: Deque[tuple[float, Any]] = deque(maxlen=self.max_frames)
        self.frame_size: Optional[Tuple[int, int]] = None

    def add(self, frame: Any, timestamp: float | None = None) -> None:
        timestamp = timestamp or time.time()
        self.frames.append((timestamp, frame.copy()))
        height, width = frame.shape[:2]
        self.frame_size = (width, height)

    def save_pre_event_clip(self, output_path: str, fps: float | None = None) -> Optional[str]:
        if not self.frames or self.frame_size is None:
            return None
        return write_video([frame for _, frame in self.frames], output_path, fps or self.fps, self.frame_size)


class EvidenceManager:
    def __init__(
        self,
        image_dir: str = "evidence/images",
        video_dir: str = "evidence/videos",
        metadata_dir: str = "evidence/metadata",
        fps: float = 20.0,
        retention_days: int = 30,
    ) -> None:
        self.image_dir = Path(image_dir)
        self.video_dir = Path(video_dir)
        self.metadata_dir = Path(metadata_dir)
        self.fps = fps
        self.retention_days = retention_days
        for directory in (self.image_dir, self.video_dir, self.metadata_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def save_frame(self, frame: Any, event_type: str, camera_id: str = "camera") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_path = self.image_dir / f"{camera_id}_{event_type}_{timestamp}.jpg"
        cv2.imwrite(str(image_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        return image_path

    def save_metadata(self, event_type: str, metadata: dict[str, Any], camera_id: str = "camera") -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.metadata_dir / f"{camera_id}_{event_type}_{timestamp}.json"
        path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True, default=str), encoding="utf-8")
        return path

    def cleanup_old_evidence(self) -> int:
        if self.retention_days <= 0:
            return 0
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0
        for directory in (self.image_dir, self.video_dir, self.metadata_dir):
            for path in directory.glob("*"):
                if path.is_file() and datetime.fromtimestamp(path.stat().st_mtime) < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed


def write_video(frames: list[Any], output_path: str, fps: float, frame_size: tuple[int, int]) -> Optional[str]:
    if not frames:
        return None
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, frame_size)
    if not writer.isOpened():
        return None
    for frame in frames:
        writer.write(frame)
    writer.release()
    return output_path

