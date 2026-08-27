import pytest
import numpy as np
from agents.vision.schemas import VisionConfig, Detection, BoundingBox
from agents.vision.pipeline.tracker import PersonTracker, TrackedPerson


class TestSchemas:
    def test_bounding_box(self):
        bbox = BoundingBox(x1=10, y1=20, x2=100, y2=200)
        assert bbox.width == 90
        assert bbox.height == 180
        assert bbox.center == (55.0, 110.0)
        d = bbox.to_dict()
        assert d["x1"] == 10
        assert d["y1"] == 20
        assert d["x2"] == 100
        assert d["y2"] == 200

    def test_detection(self):
        bbox = BoundingBox(x1=0, y1=0, x2=10, y2=10)
        det = Detection(class_id=0, class_name="person", confidence=0.9, bbox=bbox)
        assert det.confidence == 0.9
        d = det.to_dict()
        assert d["class_name"] == "person"
        assert d["bbox"]["width"] == 10

    def test_vision_config_defaults(self):
        cfg = VisionConfig()
        assert cfg.yolo_model_path == "yolov8n.pt"
        assert cfg.tracking_enabled is True
        assert cfg.tracker_confidence_threshold == 0.5
        assert cfg.tracker_max_missed_frames == 30
        assert cfg.yolo_detection_interval == 5
        assert cfg.yolo_min_confidence_for_new_track == 0.5


class TestTracker:
    def setup_method(self):
        self.config = VisionConfig()
        self.tracker = PersonTracker(self.config)

    def test_new_track(self):
        now = 1000.0
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9,
                     bbox=BoundingBox(x1=100, y1=100, x2=200, y2=200))
        ]
        tracks = self.tracker.update(detections, now)
        assert len(tracks) == 1
        assert tracks[0].track_id == 1
        assert tracks[0].center == (150.0, 150.0)

    def test_track_movement(self):
        now = 1000.0
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9,
                     bbox=BoundingBox(x1=100, y1=100, x2=200, y2=200))
        ]
        tracks = self.tracker.update(detections, now)
        track_id = tracks[0].track_id
        
        # Second frame - moved right
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9,
                     bbox=BoundingBox(x1=110, y1=100, x2=210, y2=200))
        ]
        tracks = self.tracker.update(detections, now + 1)
        assert len(tracks) == 1
        assert tracks[0].track_id == track_id
        assert tracks[0].speed > 0
        assert tracks[0].direction == "E"

    def test_two_tracks(self):
        now = 1000.0
        detections = [
            Detection(class_id=0, class_name="person", confidence=0.9,
                     bbox=BoundingBox(x1=100, y1=100, x2=200, y2=200)),
            Detection(class_id=0, class_name="person", confidence=0.8,
                     bbox=BoundingBox(x1=300, y1=100, x2=400, y2=200))
        ]
        tracks = self.tracker.update(detections, now)
        assert len(tracks) == 2
        track_ids = {t.track_id for t in tracks}
        assert track_ids == {1, 2}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
