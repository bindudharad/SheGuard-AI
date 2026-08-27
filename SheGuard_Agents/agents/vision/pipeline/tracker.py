from typing import Optional, List, Dict, Deque, Tuple
from dataclasses import dataclass, field
from collections import deque
import math
import time
import numpy as np
import cv2

from agents.vision.schemas import VisionConfig, Detection, BoundingBox


Point = Tuple[float, float]


@dataclass
class TrackedPerson:
    track_id: int
    bbox: BoundingBox
    center: Point
    last_center: Point
    last_seen: float
    speed: float = 0.0
    direction: Optional[str] = None
    distance_travelled: float = 0.0
    presence_duration: float = 0.0
    first_seen: float = field(default_factory=time.time)
    
    # Tracker confidence and quality
    tracker_confidence: float = 1.0
    match_quality: float = 1.0
    missed_frames: int = 0
    
    # Velocity and trajectory
    velocity: Point = (0.0, 0.0)
    velocity_history: Deque[Point] = field(default_factory=lambda: deque(maxlen=30))
    trajectory_history: Deque[Point] = field(default_factory=lambda: deque(maxlen=60))
    
    # Pose data
    pose: Optional[object] = None
    
    def update_trajectory(self) -> None:
        self.trajectory_history.append(self.center)
        if len(self.trajectory_history) > 1:
            prev = self.trajectory_history[-2]
            self.velocity = (self.center[0] - prev[0], self.center[1] - prev[1])
            self.velocity_history.append(self.velocity)
            self.distance_travelled += math.hypot(self.velocity[0], self.velocity[1])
            self.speed = math.hypot(self.velocity[0], self.velocity[1])
            angle = math.degrees(math.atan2(self.velocity[1], self.velocity[0]))
            if angle < 0:
                angle += 360
            self.direction = self._angle_to_direction(angle)
    
    def _angle_to_direction(self, angle: float) -> str:
        if angle >= 337.5 or angle < 22.5:
            return 'E'
        elif angle < 67.5:
            return 'NE'
        elif angle < 112.5:
            return 'N'
        elif angle < 157.5:
            return 'NW'
        elif angle < 202.5:
            return 'W'
        elif angle < 247.5:
            return 'SW'
        elif angle < 292.5:
            return 'S'
        else:
            return 'SE'
    
    def get_trajectory_similarity(self, other: 'TrackedPerson', window: int = 10) -> float:
        if len(self.trajectory_history) < 2 or len(other.trajectory_history) < 2:
            return 0.0
        self_traj = list(self.trajectory_history)[-window:]
        other_traj = list(other.trajectory_history)[-window:]
        min_len = min(len(self_traj), len(other_traj))
        if min_len < 2:
            return 0.0
        self_traj = self_traj[-min_len:]
        other_traj = other_traj[-min_len:]
        similarities = []
        for i in range(1, min_len):
            self_vec = (self_traj[i][0] - self_traj[i-1][0], self_traj[i][1] - self_traj[i-1][1])
            other_vec = (other_traj[i][0] - other_traj[i-1][0], other_traj[i][1] - other_traj[i-1][1])
            self_norm = math.hypot(*self_vec)
            other_norm = math.hypot(*other_vec)
            if self_norm > 1.0 and other_norm > 1.0:
                dot = self_vec[0] * other_vec[0] + self_vec[1] * other_vec[1]
                cos_sim = dot / (self_norm * other_norm)
                similarities.append(max(0.0, cos_sim))
        return sum(similarities) / len(similarities) if similarities else 0.0


class PersonTracker:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.tracks: Dict[int, TrackedPerson] = {}
        self.next_track_id = 1
        self.max_match_distance = config.tracking_max_distance
        self.stale_seconds = config.tracking_stale_seconds
        self.tracker_confidence_threshold = config.tracker_confidence_threshold
        self.max_missed_frames = config.tracker_max_missed_frames
        self.detection_interval = config.yolo_detection_interval
        self.frame_counter = 0
        self.last_detection_frame = -1
        self.yolo_min_confidence = config.yolo_min_confidence_for_new_track
        self.last_frame_hash = None
        self.scene_change_threshold = 0.3
        self.detection_needed = True  # Flag to signal if YOLO detection should run
        
    def _should_detect(self, frame_id: int, frame: Optional[np.ndarray] = None) -> bool:
        """
        Determine if YOLO detection should run this frame.
        Returns True on:
        - First frame
        - Detection interval reached
        - Scene change detected
        - Tracker confidence degraded
        - New person might have entered
        """
        # First frame
        if self.last_detection_frame < 0:
            self.frame_counter += 1
            self.last_detection_frame = self.frame_counter
            return True
        
        self.frame_counter += 1
        
        # Scene change check
        scene_changed = False
        if frame is not None:
            scene_changed = self._detect_scene_change(frame)
            if scene_changed:
                self.last_detection_frame = self.frame_counter - self.detection_interval
                return True
        
        # Check tracker confidence
        if self.should_force_detection():
            return True
        
        # Regular interval
        if self.frame_counter - self.last_detection_frame >= self.detection_interval:
            self.last_detection_frame = self.frame_counter
            return True
        
        return False
    
    def update(self, detections: List[Detection], now: float, frame: Optional[np.ndarray] = None) -> List[TrackedPerson]:
        """Update tracks. If detections empty, just propagate existing tracks."""
        # Check if we should run detection this frame
        if frame is not None:
            self.detection_needed = self._should_detect(self.frame_counter, frame)
        
        if not detections:
            return self._propagate_tracks(now)
        
        return self._update_with_detections(detections, now)
    
    def _detect_scene_change(self, frame: np.ndarray) -> bool:
        try:
            small = cv2.resize(frame, (64, 64), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            frame_hash = cv2.dct(np.float32(gray))
            if self.last_frame_hash is not None:
                diff = np.abs(frame_hash - self.last_frame_hash)
                change_score = float(np.mean(diff))
                self.last_frame_hash = frame_hash
                return change_score > self.scene_change_threshold
            self.last_frame_hash = frame_hash
            return False
        except Exception:
            return False
    
    def _update_with_detections(self, detections: List[Detection], now: float) -> List[TrackedPerson]:
        assigned_track_ids = set()
        updated_tracks: Dict[int, TrackedPerson] = {}
        for detection in detections:
            if detection.confidence < self.yolo_min_confidence:
                continue
            center = detection.bbox.center
            best_track = None
            best_distance = float('inf')
            for track in self.tracks.values():
                if track.track_id in assigned_track_ids:
                    continue
                distance = self._point_distance(center, track.center)
                if distance < best_distance and distance < self.max_match_distance:
                    best_distance = distance
                    best_track = track
            if best_track is None:
                track = TrackedPerson(
                    track_id=self.next_track_id,
                    bbox=detection.bbox,
                    center=center,
                    last_center=center,
                    last_seen=now,
                )
                self.next_track_id += 1
                track.tracker_confidence = detection.confidence
            else:
                track = best_track
                track.last_center = track.center
                track.center = center
                track.bbox = detection.bbox
                track.last_seen = now
                track.missed_frames = 0
                track.tracker_confidence = min(1.0, track.tracker_confidence + 0.1)
                track.match_quality = 1.0 - min(1.0, best_distance / self.max_match_distance)
                assigned_track_ids.add(track.track_id)
            track.update_trajectory()
            track.presence_duration = now - track.first_seen
            updated_tracks[track.track_id] = track
        for track_id, track in self.tracks.items():
            if track_id in updated_tracks or track_id in assigned_track_ids:
                continue
            track.missed_frames += 1
            track.tracker_confidence *= 0.85
            if track.missed_frames <= self.max_missed_frames and track.tracker_confidence >= self.tracker_confidence_threshold:
                track.last_seen = now
                track.speed = 0.0
                updated_tracks[track_id] = track
        
        self.tracks = updated_tracks
        return list(self.tracks.values())
    
    def _propagate_tracks(self, now: float) -> List[TrackedPerson]:
        updated_tracks: Dict[int, TrackedPerson] = {}
        for track_id, track in self.tracks.items():
            track.missed_frames += 1
            track.tracker_confidence *= 0.9
            if track.missed_frames <= self.max_missed_frames and track.tracker_confidence >= self.tracker_confidence_threshold:
                # Predict position based on velocity
                predicted_center = (
                    track.center[0] + track.velocity[0],
                    track.center[1] + track.velocity[1]
                )
                track.last_center = track.center
                track.center = predicted_center
                w = track.bbox.width
                h = track.bbox.height
                track.bbox = BoundingBox(
                    x1=int(predicted_center[0] - w/2),
                    y1=int(predicted_center[1] - h/2),
                    x2=int(predicted_center[0] + w/2),
                    y2=int(predicted_center[1] + h/2)
                )
                track.last_seen = now
                track.missed_frames += 1
                track.tracker_confidence *= 0.9
                if track.missed_frames <= self.max_missed_frames and track.tracker_confidence >= self.tracker_confidence_threshold:
                    track.presence_duration = now - track.first_seen
                    track.update_trajectory()
                    updated_tracks[track_id] = track
        self.tracks = {
            track_id: track
            for track_id, track in updated_tracks.items()
            if now - track.last_seen < self.stale_seconds
        }
        return list(self.tracks.values())
    
    def _point_distance(self, a: Point, b: Point) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)
    
    def get_track(self, track_id: int) -> Optional[TrackedPerson]:
        return self.tracks.get(track_id)
    
    def get_all_tracks(self) -> List[TrackedPerson]:
        return list(self.tracks.values())
    
    def should_force_detection(self) -> bool:
        for track in self.tracks.values():
            if track.tracker_confidence < self.tracker_confidence_threshold:
                return True
        return False
    
    def reset_detection_timer(self) -> None:
        self.last_detection_frame = -self.detection_interval
