from typing import Optional, List, Dict, Deque
from dataclasses import dataclass, field
from collections import deque
import numpy as np
import cv2
import time

from agents.vision.schemas import VisionConfig


@dataclass
class TrackTemporalState:
    track_id: int
    sequence: Deque[np.ndarray] = field(default_factory=lambda: deque(maxlen=16))
    previous_frame: Optional[np.ndarray] = None
    last_seen: float = 0.0
    last_bbox: Optional[tuple] = None


class TemporalBuffer:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.sequence_length = config.temporal_sequence_length
        self.track_states: Dict[int, TrackTemporalState] = {}
        self.feature_dim = 116  # 108 pose + 8 motion features
        
    def add_frame_features(self, track_id: int, features: np.ndarray, 
                           frame: np.ndarray, bbox: tuple, now: float) -> None:
        if track_id not in self.track_states:
            self.track_states[track_id] = TrackTemporalState(track_id=track_id)
            
        state = self.track_states[track_id]
        state.sequence.append(features.astype(np.float32))
        state.previous_frame = frame.copy()
        state.last_seen = now
        state.last_bbox = bbox
        
    def get_sequence(self, track_id: int) -> Optional[np.ndarray]:
        if track_id not in self.track_states:
            return None
            
        state = self.track_states[track_id]
        if len(state.sequence) == 0:
            return None
            
        # Pad or trim to sequence_length
        rows = list(state.sequence)
        if len(rows) >= self.sequence_length:
            sequence = np.stack(rows[-self.sequence_length:])
        else:
            padding = [np.zeros_like(rows[0], dtype=np.float32) 
                      for _ in range(self.sequence_length - len(rows))]
            sequence = np.stack(padding + rows)
            
        return sequence.astype(np.float32)
    
    def is_ready(self, track_id: int, min_frames: int = 8) -> bool:
        if track_id not in self.track_states:
            return False
        return len(self.track_states[track_id].sequence) >= min_frames
    
    def get_buffered_count(self, track_id: int) -> int:
        if track_id not in self.track_states:
            return 0
        return len(self.track_states[track_id].sequence)
    
    def cleanup_stale(self, now: float, stale_seconds: float = 3.0) -> None:
        stale = [
            track_id for track_id, state in self.track_states.items()
            if now - state.last_seen > stale_seconds
        ]
        for track_id in stale:
            del self.track_states[track_id]
    
    def clear(self) -> None:
        self.track_states.clear()
