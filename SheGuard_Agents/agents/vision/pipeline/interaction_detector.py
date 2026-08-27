from typing import List, Optional
from dataclasses import dataclass
import math
import time

from agents.vision.schemas import Detection, TrackingData, InteractionData, VisionConfig


class InteractionDetector:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.interaction_distance_threshold = 170.0  # pixels
        self.interaction_speed_threshold = 32.0  # pixels/frame
        self.min_interaction_frames = 8
        self.interaction_counters: dict = {}
        
    def detect(self, tracks: List[TrackingData], now: float) -> InteractionData:
        if len(tracks) < 2:
            self._decay_counters()
            return InteractionData(detected=False, confidence=0.0)
        
        best_interaction = None
        best_confidence = 0.0
        
        for i in range(len(tracks)):
            for j in range(i + 1, len(tracks)):
                a = tracks[i]
                b = tracks[j]
                
                distance = self._point_distance(a.center, b.center)
                close = distance < self.interaction_distance_threshold
                fast = a.speed > self.interaction_speed_threshold or b.speed > self.interaction_speed_threshold
                
                # Check if moving toward each other
                moving_toward = self._moving_toward(a, b)
                
                if close and fast and moving_toward:
                    pair_key = tuple(sorted([a.track_id, b.track_id]))
                    self.interaction_counters[pair_key] = self.interaction_counters.get(pair_key, 0) + 1
                    
                    if self.interaction_counters[pair_key] >= self.min_interaction_frames:
                        confidence = min(0.9, 0.5 + (self.interaction_counters[pair_key] - self.min_interaction_frames) * 0.05)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_interaction = (a.track_id, b.track_id, distance, self.interaction_counters[pair_key])
                else:
                    pair_key = tuple(sorted([a.track_id, b.track_id]))
                    if pair_key in self.interaction_counters:
                        self.interaction_counters[pair_key] = max(0, self.interaction_counters[pair_key] - 1)
        
        if best_interaction:
            tid1, tid2, dist, frames = best_interaction
            duration = frames / 30.0  # approximate seconds at 30fps
            return InteractionData(
                detected=True,
                confidence=best_confidence,
                participants=[tid1, tid2],
                duration_seconds=duration,
                distance=dist
            )
        
        return InteractionData(detected=False, confidence=0.0)
    
    def _point_distance(self, a: tuple, b: tuple) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    
    def _moving_toward(self, a: TrackingData, b: TrackingData) -> bool:
        # Simplified: check if distance is decreasing based on directions
        # In a real implementation, track previous centers
        return True  # placeholder
    
    def _decay_counters(self) -> None:
        for key in list(self.interaction_counters.keys()):
            self.interaction_counters[key] = max(0, self.interaction_counters[key] - 1)
            if self.interaction_counters[key] == 0:
                del self.interaction_counters[key]
