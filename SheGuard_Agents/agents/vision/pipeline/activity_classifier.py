from typing import Optional, List
from dataclasses import dataclass
import numpy as np

from agents.vision.schemas import VisionConfig, ActivityData, TrackingData
from agents.vision.models.gru_adapter import GRUAdapter, GRUPrediction
from agents.vision.pipeline.temporal_buffer import TemporalBuffer


@dataclass
class FrameFeatures:
    pose_features: np.ndarray  # 108 dims
    motion_features: np.ndarray  # 8 dims
    combined: np.ndarray  # 116 dims
    pose_confidence: float


class FeatureExtractor:
    def __init__(self, config: VisionConfig):
        self.config = config
        
    def extract(self, frame: np.ndarray, previous_frame: Optional[np.ndarray],
                bbox: tuple, track_id: int, pose_keypoints: List[tuple],
                pose_visible: bool, pose_confidence: float,
                pose_head: Optional[tuple], pose_hip: Optional[tuple],
                pose_shoulder: Optional[tuple]) -> Optional[FrameFeatures]:
        if not pose_visible or len(pose_keypoints) < 9:
            return None
            
        try:
            # Normalize keypoints to bbox
            x1, y1, x2, y2 = bbox
            bbox_w = x2 - x1
            bbox_h = y2 - y1
            
            # Center at hip/shoulder midpoint
            center_x = (pose_hip[0] + pose_shoulder[0]) / 2 if pose_hip and pose_shoulder else (x1 + x2) / 2
            center_y = (pose_hip[1] + pose_shoulder[1]) / 2 if pose_hip and pose_shoulder else (y1 + y2) / 2
            
            scale = max(bbox_w, bbox_h, 40.0)
            
            # Normalize keypoints (9 keypoints * 2 = 18)
            normalized = []
            for kp in pose_keypoints:
                nx = (kp[0] - center_x) / scale
                ny = (kp[1] - center_y) / scale
                normalized.extend([nx, ny])
            
            # Visibility scores (9)
            visibilities = [1.0] * len(pose_keypoints)  # simplified
            
            # Body angles (6)
            angles = self._compute_angles(pose_keypoints)
            
            # Temporal features (3): speed, posture_ratio, inactivity
            speed = 0.0  # will be filled by tracker
            posture_ratio = bbox_w / max(bbox_h, 1)
            inactivity = 0.0
            
            pose_features = np.array(normalized + visibilities + angles + [speed, posture_ratio, inactivity], dtype=np.float32)
            
            # Motion features (8) - optical flow based
            motion = self._compute_motion(frame, previous_frame)
            
            combined = np.concatenate([pose_features, motion])
            
            return FrameFeatures(
                pose_features=pose_features,
                motion_features=motion,
                combined=combined,
                pose_confidence=pose_confidence
            )
        except Exception as e:
            print(f"[FeatureExtractor] Error: {e}")
            return None
    
    def _compute_angles(self, keypoints: List[tuple]) -> List[float]:
        # keypoints order: nose, ls, rs, le, re, lh, rh, lk, rk
        if len(keypoints) < 9:
            return [0.0] * 6
            
        def angle(a, b, c):
            ba = np.array([a[0]-b[0], a[1]-b[1]])
            bc = np.array([c[0]-b[0], c[1]-b[1]])
            denom = np.linalg.norm(ba) * np.linalg.norm(bc)
            if denom < 1e-6:
                return 0.0
            cos = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
            return np.degrees(np.arccos(cos))
        
        # Left elbow, Right elbow, Left knee, Right knee, Left hip-shoulder-knee, Right hip-shoulder-knee
        return [
            angle(keypoints[1], keypoints[3], (0,0)),  # L shoulder-elbow-wrist (approx)
            angle(keypoints[2], keypoints[4], (0,0)),  # R shoulder-elbow-wrist
            angle(keypoints[5], keypoints[7], (0,0)),  # L hip-knee-ankle
            angle(keypoints[6], keypoints[8], (0,0)),  # R hip-knee-ankle
            angle(keypoints[1], keypoints[5], keypoints[7]),  # L shoulder-hip-knee
            angle(keypoints[2], keypoints[6], keypoints[8]),  # R shoulder-hip-knee
        ]
    
    def _compute_motion(self, current: np.ndarray, previous: Optional[np.ndarray]) -> np.ndarray:
        if previous is None:
            return np.zeros(8, dtype=np.float32)
            
        gray_c = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
        gray_p = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
        gray_c = cv2.resize(gray_c, (160, 160), interpolation=cv2.INTER_AREA)
        gray_p = cv2.resize(gray_p, (160, 160), interpolation=cv2.INTER_AREA)
        diff = cv2.absdiff(gray_c, gray_p).astype(np.float32) / 255.0
        
        mean_diff = float(diff.mean())
        std_diff = float(diff.std())
        motion_area = float((diff > 0.08).mean())
        
        flow = cv2.calcOpticalFlowFarneback(
            gray_p, gray_c, None,
            pyr_scale=0.5, levels=2, winsize=13,
            iterations=2, poly_n=5, poly_sigma=1.1, flags=0
        )
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        return np.array([
            mean_diff, std_diff, motion_area,
            float(mag.mean()), float(mag.std()), float(np.percentile(mag, 90)),
            float(np.sin(ang).mean()), float(np.cos(ang).mean())
        ], dtype=np.float32)


import cv2


class ActivityClassifier:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.gru = GRUAdapter(config)
        self.temporal_buffer = TemporalBuffer(config)
        self.feature_extractor = FeatureExtractor(config)
        self.gru_loaded = False
        
    def initialize(self) -> bool:
        if self.config.temporal_enabled:
            self.gru_loaded = self.gru.load()
        return True
    
    def classify(self, track: TrackingData, frame: np.ndarray, 
                 previous_frame: Optional[np.ndarray], now: float) -> ActivityData:
        # Extract features
        pose = track.pose
        if not pose or not pose.visible:
            return ActivityData(
                label="unknown",
                confidence=0.0,
                model_status="NO_POSE"
            )
        
        features = self.feature_extractor.extract(
            frame, previous_frame, 
            (track.bbox.x1, track.bbox.y1, track.bbox.x2, track.bbox.y2),
            track.track_id,
            pose.keypoints, pose.visible, pose.confidence,
            pose.head, pose.hip, pose.shoulder
        )
        
        if features is None:
            return ActivityData(
                label="unknown",
                confidence=0.0,
                model_status="FEATURE_EXTRACTION_FAILED"
            )
        
        # Add to temporal buffer
        self.temporal_buffer.add_frame_features(
            track.track_id, features.combined, frame,
            (track.bbox.x1, track.bbox.y1, track.bbox.x2, track.bbox.y2), now
        )
        
        # Check if ready for GRU
        if self.config.temporal_enabled and self.gru_loaded:
            if self.temporal_buffer.is_ready(track.track_id):
                sequence = self.temporal_buffer.get_sequence(track.track_id)
                if sequence is not None:
                    prediction = self.gru.predict(sequence)
                    if prediction:
                        return ActivityData(
                            label=prediction.label,
                            confidence=prediction.confidence,
                            temporal_confidence=prediction.confidence,
                            sequence_length=prediction.sequence_length,
                            model_status=prediction.model_status,
                            evidence=[f"GRU: {k}={v:.2f}" for k, v in prediction.probabilities.items()]
                        )
        
        # Fallback: rule-based or not ready
        buffered = self.temporal_buffer.get_buffered_count(track.track_id)
        if buffered < 8:
            return ActivityData(
                label="warming_up",
                confidence=0.0,
                temporal_confidence=0.0,
                sequence_length=self.config.temporal_sequence_length,
                model_status="WARMING_UP",
                evidence=[f"Frames buffered: {buffered}/{self.config.temporal_sequence_length}"]
            )
        
        # Basic rule-based classification based on movement
        if track.speed > 10:
            return ActivityData(
                label="rapid_movement",
                confidence=0.6,
                evidence=[f"High speed: {track.speed:.1f} px/frame"]
            )
        
        return ActivityData(
            label="normal",
            confidence=0.5,
            evidence=["Default classification"]
        )
    
    def cleanup_stale(self, now: float) -> None:
        self.temporal_buffer.cleanup_stale(now)
    
    def close(self) -> None:
        self.gru.close()
        self.temporal_buffer.clear()

