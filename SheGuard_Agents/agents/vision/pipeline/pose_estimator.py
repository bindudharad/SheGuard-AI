from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from agents.vision.schemas import VisionConfig, BoundingBox


Point = Tuple[float, float]


@dataclass
class PoseResult:
    track_id: int
    landmarks: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)  # name -> (x, y, visibility)
    keypoints: List[Point] = field(default_factory=list)
    head: Optional[Point] = None
    hip: Optional[Point] = None
    shoulder: Optional[Point] = None
    visible: bool = False
    confidence: float = 0.0


class MediaPipePoseEstimator:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.landmarker = None
        self._initialized = False
        
    def initialize(self) -> bool:
        try:
            model_path = 'models/mediapipe/pose_landmarker_lite.task'
            base_options = mp_python.BaseOptions(model_asset_path=model_path)
            options = mp_vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.IMAGE,
                num_poses=5,
                min_pose_detection_confidence=self.config.pose_min_detection_confidence,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=self.config.pose_min_tracking_confidence,
                output_segmentation_masks=False,
            )
            self.landmarker = mp_vision.PoseLandmarker.create_from_options(options)
            self._initialized = True
            return True
        except Exception as e:
            print(f'[MediaPipe] Failed to initialize: {e}')
            import traceback
            traceback.print_exc()
            return False
    
    def estimate(self, frame: np.ndarray, bbox: BoundingBox, track_id: int) -> Optional[PoseResult]:
        if not self._initialized or self.landmarker is None:
            return None
            
        try:
            x1, y1, x2, y2 = bbox.x1, bbox.y1, bbox.x2, bbox.y2
            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                return None
                
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.landmarker.detect(mp_image)
            
            if not result.pose_landmarks or len(result.pose_landmarks) == 0:
                return None
                
            landmarks = result.pose_landmarks[0]  # First detected pose
            crop_h, crop_w = crop.shape[:2]
            
            # Key landmark indices (MediaPipe PoseLandmark enum values)
            key_indices = {
                'NOSE': 0,
                'LEFT_SHOULDER': 11,
                'RIGHT_SHOULDER': 12,
                'LEFT_ELBOW': 13,
                'RIGHT_ELBOW': 14,
                'LEFT_HIP': 23,
                'RIGHT_HIP': 24,
                'LEFT_KNEE': 25,
                'RIGHT_KNEE': 26,
                'LEFT_ANKLE': 27,
                'RIGHT_ANKLE': 28,
            }
            
            landmarks_dict = {}
            keypoints = []
            visibilities = []
            
            for name, idx in key_indices.items():
                if idx < len(landmarks):
                    lm = landmarks[idx]
                    if lm.visibility >= 0.35:
                        x = x1 + lm.x * crop_w
                        y = y1 + lm.y * crop_h
                        landmarks_dict[name] = (x, y, lm.visibility)
                        keypoints.append((x, y))
                        visibilities.append(lm.visibility)
            
            # Compute head, hip, shoulder
            nose = landmarks[0] if len(landmarks) > 0 else None
            left_hip = landmarks[23] if len(landmarks) > 23 else None
            right_hip = landmarks[24] if len(landmarks) > 24 else None
            left_shoulder = landmarks[11] if len(landmarks) > 11 else None
            right_shoulder = landmarks[12] if len(landmarks) > 12 else None
            
            head = None
            hip = None
            shoulder = None
            
            if nose:
                head = (x1 + nose.x * crop_w, y1 + nose.y * crop_h)
            if left_hip and right_hip:
                hip = ((x1 + left_hip.x * crop_w + x1 + right_hip.x * crop_w) / 2,
                       (y1 + left_hip.y * crop_h + y1 + right_hip.y * crop_h) / 2)
            if left_shoulder and right_shoulder:
                shoulder = ((x1 + left_shoulder.x * crop_w + x1 + right_shoulder.x * crop_w) / 2,
                           (y1 + left_shoulder.y * crop_h + y1 + right_shoulder.y * crop_h) / 2)
            
            avg_vis = sum(visibilities) / len(visibilities) if visibilities else 0.0
            
            return PoseResult(
                track_id=track_id,
                landmarks=landmarks_dict,
                keypoints=keypoints,
                head=head,
                hip=hip,
                shoulder=shoulder,
                visible=len(keypoints) > 0,
                confidence=avg_vis
            )
        except Exception as e:
            print(f'[MediaPipe] Estimation error: {e}')
            import traceback
            traceback.print_exc()
            return None
    
    def close(self):
        if self.landmarker:
            self.landmarker.close()
            self.landmarker = None
        self._initialized = False
