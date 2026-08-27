from typing import Optional, Generator
from dataclasses import dataclass
from enum import Enum
import cv2
import numpy as np
from pathlib import Path
import time

from agents.vision.schemas import VideoSourceType, VisionConfig


class VideoSourceError(Exception):
    def __init__(self, error_type: str, message: str, recoverable: bool = True):
        self.error_type = error_type
        self.recoverable = recoverable
        super().__init__(message)


@dataclass
class VideoFrame:
    frame: np.ndarray
    frame_id: int
    timestamp: float
    source: str
    
    
class VideoSource:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.cap: Optional[cv2.VideoCapture] = None
        self.source_str = config.video_source
        self.source_type = config.video_source_type
        self.frame_id = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2.0
        
    def open(self) -> bool:
        try:
            # In simulation mode, do not require a real video device/frame
            if getattr(self.config, "simulation_mode", False):
                self.cap = None
                self.reconnect_attempts = 0
                return True

            if self.source_type == VideoSourceType.WEBCAM:
                source_idx = int(self.source_str)
                self.cap = cv2.VideoCapture(source_idx)
            elif self.source_type == VideoSourceType.FILE:
                self.cap = cv2.VideoCapture(self.source_str)
            elif self.source_type == VideoSourceType.RTSP:
                self.cap = cv2.VideoCapture(self.source_str)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            elif self.source_type == VideoSourceType.DROIDCAM:
                # Try DroidCam indices 1, 2
                for idx in [1, 2]:
                    self.cap = cv2.VideoCapture(idx)
                    if self.cap.isOpened():
                        ok, _ = self.cap.read()
                        if ok:
                            self.source_str = str(idx)
                            break
                    self.cap.release()
                else:
                    self.cap = cv2.VideoCapture(0)
            else:
                raise VideoSourceError(
                    'INVALID_SOURCE_TYPE',
                    f'Unknown source type: {self.source_type}',
                    recoverable=False
                )
            
            if not self.cap or not self.cap.isOpened():
                raise VideoSourceError(
                    'VIDEO_SOURCE_UNAVAILABLE',
                    f'Unable to open video source: {self.source_str}',
                    recoverable=True
                )
            
            # Test read
            ok, frame = self.cap.read()
            if not ok or frame is None:
                raise VideoSourceError(
                    'FRAME_READ_ERROR',
                    'Video source opened but cannot read frames',
                    recoverable=True
                )
                
            self.reconnect_attempts = 0
            return True
            
        except VideoSourceError:
            raise
        except Exception as e:
            raise VideoSourceError(
                'VIDEO_SOURCE_ERROR',
                f'Failed to open video source: {e}',
                recoverable=True
            )
    
    def read(self) -> Optional[VideoFrame]:
        # Simulation mode: generate synthetic frame
        if getattr(self.config, "simulation_mode", False) or self.cap is None:
            # Create a synthetic frame (blank or with test pattern)
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add a simple test pattern
            cv2.rectangle(frame, (100, 100), (300, 300), (255, 255, 255), -1)
            cv2.rectangle(frame, (400, 200), (550, 350), (200, 200, 200), -1)
            
            self.frame_id += 1
            return VideoFrame(
                frame=frame,
                frame_id=self.frame_id,
                timestamp=time.time(),
                source="simulation"
            )
        
        if not self.cap or not self.cap.isOpened():
            return None
            
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return None
            
        self.frame_id += 1
        return VideoFrame(
            frame=frame,
            frame_id=self.frame_id,
            timestamp=time.time(),
            source=self.source_str
        )
    
    def reconnect(self) -> bool:
        self.close()
        for attempt in range(1, self.max_reconnect_attempts + 1):
            self.reconnect_attempts = attempt
            time.sleep(self.reconnect_delay)
            try:
                if self.open():
                    return True
            except VideoSourceError:
                continue
        return False
    
    def close(self) -> None:
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def is_opened(self) -> bool:
        if getattr(self.config, "simulation_mode", False):
            return True
        return self.cap is not None and self.cap.isOpened()
    
    def get_fps(self) -> float:
        if self.cap:
            return self.cap.get(cv2.CAP_PROP_FPS)
        return 30.0  # simulation default
    
    def get_frame_size(self) -> tuple:
        if self.cap:
            w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            return (w, h)
        return (640, 480)  # simulation default
