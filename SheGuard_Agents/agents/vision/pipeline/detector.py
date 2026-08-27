from typing import List, Optional
from dataclasses import dataclass
import cv2
import numpy as np
from ultralytics import YOLO

from agents.vision.schemas import Detection, BoundingBox, VisionConfig


@dataclass
class YOLODetection:
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox


class YOLODetector:
    def __init__(self, config: VisionConfig):
        self.config = config
        self.model: Optional[YOLO] = None
        self.device = self._resolve_device()
        
    def _resolve_device(self) -> str:
        if self.config.yolo_device == 'auto':
            try:
                import torch
                if torch.cuda.is_available():
                    return 'cuda'
            except ImportError:
                pass
            return 'cpu'
        return self.config.yolo_device
    
    def load(self) -> bool:
        try:
            model_path = self.config.yolo_model_path
            self.model = YOLO(model_path)
            self.model.to(self.device)
            return True
        except Exception as e:
            print(f'[YOLO] Failed to load model: {e}')
            return False
    
    def detect(self, frame: np.ndarray) -> List[YOLODetection]:
        if self.model is None:
            return []
            
        try:
            results = self.model.predict(
                frame,
                classes=[0],  # person only
                conf=self.config.yolo_confidence,
                iou=self.config.yolo_iou,
                imgsz=self.config.yolo_image_size,
                device=self.device,
                verbose=False
            )
            
            detections = []
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    
                    # Clamp to frame bounds
                    h, w = frame.shape[:2]
                    x1 = max(0, min(x1, w - 1))
                    y1 = max(0, min(y1, h - 1))
                    x2 = max(0, min(x2, w - 1))
                    y2 = max(0, min(y2, h - 1))
                    
                    if x2 > x1 and y2 > y1:
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = self.model.names.get(class_id, 'unknown')
                        
                        detections.append(YOLODetection(
                            class_id=class_id,
                            class_name=class_name,
                            confidence=confidence,
                            bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                        ))
            
            return detections
            
        except Exception as e:
            print(f'[YOLO] Detection error: {e}')
            return []
    
    def close(self) -> None:
        self.model = None
