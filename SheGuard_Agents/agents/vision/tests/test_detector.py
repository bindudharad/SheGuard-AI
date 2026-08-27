import pytest
import numpy as np
from agents.vision.schemas import VisionConfig, BoundingBox
from agents.vision.pipeline.detector import YOLODetector, YOLODetection


class TestDetector:
    def test_yolo_detection_dataclass(self):
        bbox = BoundingBox(x1=100, y1=100, x2=200, y2=200)
        det = YOLODetection(class_id=0, class_name='person', confidence=0.9, bbox=bbox)
        assert det.class_id == 0
        assert det.class_name == 'person'
        assert det.confidence == 0.9
        assert det.bbox.width == 100
    
    def test_detector_creation(self):
        config = VisionConfig()
        detector = YOLODetector(config)
        assert detector.config == config
        assert detector.model is None
        assert detector.device in ('cpu', 'cuda')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
