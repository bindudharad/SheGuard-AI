# Vision Agent - Existing AI Audit Report

**Date**: 2026-08-17  
**Component**: SheGuard_AI  
**Purpose**: Document existing computer vision components for Vision Agent implementation

---

## 1. Existing YOLO Model

### 1.1 Model File
- **Path**: C:\Programs\codex\SheGuard\SheGuard_AI\yolov8n.pt
- **Size**: 6,549,796 bytes (~6.5 MB)
- **Type**: Ultralytics YOLOv8 nano
- **Task**: Object Detection (COCO dataset)
- **Classes**: 80 classes (person = class 0)

### 1.2 YOLO Usage in Existing Code
**File**: SheGuard_AI/utils/detection.py::LocalSafetyAnalyzer
- Model loaded in __init__: self.model = YOLO(yolo_model)
- Default model: yolov8n.pt
- Person confidence threshold: 0.45
- Classes filtered: [0] (person only)
- Inference: self.model.predict(frame, classes=[0], conf=0.45, verbose=False)

**File**: SheGuard_AI/utils/feature_extractor.py::PoseFeatureExtractor
- Same YOLO model reused
- Person confidence threshold: 0.35 (lower for feature extraction)
- Device configurable via device parameter

### 1.3 YOLO Output Format
`python
# From detection.py
boxes: List[BBox] = []  # BBox = Tuple[int, int, int, int] = (x1, y1, x2, y2)
for box in result.boxes:
    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
    # Clamped to frame bounds
`

---

## 2. Existing MediaPipe Pose Implementation

### 2.1 Configuration
- **Library**: mediapipe.solutions.pose
- **Model Complexity**: 1 (balanced speed/accuracy)
- **Static Image Mode**: False (video streaming mode)
- **Min Detection Confidence**: 0.45
- **Min Tracking Confidence**: 0.45

### 2.2 Landmarks Extracted (33 total)
Key landmarks used in existing code:
| Index | Name | Usage |
|-------|------|-------|
| 0 | NOSE | Head position |
| 11 | LEFT_SHOULDER | Shoulder line |
| 12 | RIGHT_SHOULDER | Shoulder line |
| 13 | LEFT_ELBOW | Arm pose |
| 14 | RIGHT_ELBOW | Arm pose |
| 23 | LEFT_HIP | Hip line |
| 24 | RIGHT_HIP | Hip line |
| 25 | LEFT_KNEE | Leg pose |
| 26 | RIGHT_KNEE | Leg pose |
| 27 | LEFT_ANKLE | - |
| 28 | RIGHT_ANKLE | - |

### 2.3 Pose Output Structure
**File**: SheGuard_AI/utils/detection.py::PoseInfo
`python
@dataclass
class PoseInfo:
    head: Optional[Point] = None          # NOSE
    hip: Optional[Point] = None           # Average of LEFT_HIP, RIGHT_HIP
    shoulder: Optional[Point] = None      # Average of LEFT_SHOULDER, RIGHT_SHOULDER
    keypoints: List[Point] = []           # 9 tracked keypoints
    visible: bool = False                 # head and hip both detected
`

**File**: SheGuard_AI/utils/feature_extractor.py returns FeatureResult with:
- features: np.ndarray (138 features: 33*2 coords + 33 visibility + 6 angles + 3 temporal)
- bbox: Optional[BBox]
- keypoints: List[Point]
- confidence: float (mean visibility)
- posture_ratio: float (width/height)
- movement_speed: float
- inactivity_duration: float

---

## 3. Existing GRU / Temporal Model

### 3.1 Model Files
| File | Size | Purpose |
|------|------|---------|
| models/v2/sheguard_sequence_model.pt | 815,417 bytes | PyTorch GRU checkpoint |
| models/v2/sequence_scaler.joblib | 3,399 bytes | StandardScaler for features |
| models/v2/sequence_label_encoder.joblib | 423 bytes | LabelEncoder for classes |

### 3.2 Model Architecture (from metrics_v2.json & train_v2.py)
- **Type**: 2-layer GRU + Classification Head
- **Input Size**: 116 features per frame (SEQUENCE_FEATURE_LENGTH)
- **Sequence Length**: 16 frames
- **Hidden Size**: 128 (from training args default)
- **Num Layers**: 2
- **Bidirectional**: False
- **Dropout**: 0.25 (training), 0.0 (inference)
- **Output Classes**: 4 (attack, fall, fight, normal)

### 3.3 Model Checkpoint Structure
`python
{
    "model_state": state_dict,
    "input_size": 116,
    "hidden_size": 128,
    "num_classes": 4,
    "classes": ["attack", "fall", "fight", "normal"],
    "sequence_length": 16,
    "model_type": "gru"
}
`

### 3.4 GRU Inference Code
**File**: SheGuard_AI/action_sequence_classifier.py::ActionSequenceClassifier
- Loads checkpoint with weights_only=False (PyTorch 2.6 compatibility)
- Reconstructs SequenceGRU architecture
- Uses feature_extractor for pose features + motion_features for optical flow
- Smoothing: 8-frame window, majority vote + probability averaging
- Persistence: 3 frames minimum for label activation
- Trigger confidence: 0.72, Clear confidence: 0.52

### 3.5 Sequence Features (116 = 108 pose + 8 motion)
**Pose Features** (from feature_extractor.py feature_length()):
- 33 keypoints * 2 = 66 (normalized x,y)
- 33 visibility scores = 33
- 6 body angles = 6
- 3 temporal = 3 (speed, posture_ratio, inactivity)
- **Total**: 108

**Motion Features** (from sequence_features.py):
- Mean diff, Std diff, Motion area
- Optical flow magnitude: mean, std, 90th percentile
- Optical flow angle: sin mean, cos mean
- **Total**: 8

---

## 4. Existing Tracking Implementation

### 4.1 SimpleTracker
**File**: SheGuard_AI/utils/tracking.py::SimpleTracker
- **Algorithm**: Centroid-based matching with Hungarian-style assignment
- **Max Match Distance**: 120 pixels (configurable)
- **Stale Threshold**: 1.5 seconds
- **Track State** (PersonTrack):
  - track_id: int
  - bbox: BBox
  - center: Point
  - last_center: Point
  - last_seen: float (timestamp)
  - speed: float (pixels/frame)
  - still_since: Optional[float]
  - no_movement_alerted: bool
  - fall_counter: int
  - last_head_hip_delta: Optional[float]
  - pose: PoseInfo
  - last_keypoints: List[Point]

### 4.2 Tracking Features Computed
- Center point per frame
- Speed (pixel distance between consecutive centers)
- Direction implied by center movement
- Presence duration via last_seen

---

## 5. Existing Video Input Pipeline

### 5.1 Supported Sources (main.py)
- **DroidCam**: Camera indices 1, 2 (auto-tries both)
- **RTSP/IP Camera**: URL support via --source
- **Video Files**: Local file paths
- **USB Camera**: Index 0 (ignored by default for DroidCam)

### 5.2 Frame Processing (HybridSafetySystem.run())
`python
while True:
    ok, frame = cap.read()
    if not ok: reconnect()
    
    clip_buffer.add(frame)
    
    if frame_index % frame_skip == 0:
        tracks, events = local_ai.analyze_frame(frame, now)
        classifier_event = classifier_event(frame, tracks)
    else:
        tracks, events = last_tracks, []
    
    handle_events(frame, events, now)
    draw_output(frame, tracks, now)
    window.show(frame)
`

### 5.3 Frame Skip
- Configurable via --frame-skip (default: 1)
- Runs AI every N frames for CPU optimization

### 5.4 Event Clip Buffer
**File**: SheGuard_AI/video_clipper.py::EventClipBuffer
- Rolling frame buffer (deque)
- Saves pre/post event video clips
- Output: MP4 files

---

## 6. Existing Detection Logic (Rule-Based)

### 6.1 Fall Detection (LocalSafetyAnalyzer.detect_fall)
- Head below hip + 20px offset
- Sudden head-hip delta change > 45px
- Lying shape: bbox width > height * 1.15
- Persistence: 6 consecutive frames

### 6.2 Unconscious/No Movement (detect_no_movement)
- Keypoint movement < 8px AND center movement < 10px
- Duration: 5 seconds
- Alerts once per still period

### 6.3 Attack Detection (detect_attack)
- Requires 2+ persons
- Inter-person distance < 170px
- At least one person speed > 32px/frame
- Distance decreasing (moving toward each other)
- Persistence: 8 consecutive frames

---

## 7. Existing Legacy ML Classifier

### 7.1 Model Files
| File | Size | Type |
|------|------|------|
| models/model.joblib | 678,873 bytes | scikit-learn MLPClassifier |
| models/scaler.joblib | 3,207 bytes | StandardScaler |
| models/label_encoder.joblib | 423 bytes | LabelEncoder |

### 7.2 Classes
- fall, attack, fight, normal

### 7.3 Usage
- Single-frame pose features -> MLP
- Confidence threshold: 0.75
- Fallback when GRU unavailable

---

## 8. Existing Dependencies

`
opencv-python
mediapipe==0.10.14
ultralytics
numpy
torch
scikit-learn
joblib
`

---

## 9. Existing Bugs / Issues Identified

1. **GRU Model Loading**: Uses weights_only=False due to PyTorch 2.6 compatibility - security consideration
2. **DroidCam Reconnect**: Basic retry logic but no exponential backoff
3. **Frame Processing**: No frame queue - processes synchronously, can drop frames
4. **Memory**: No explicit cleanup of old track histories in temporal classifier
5. **Video Validation**: Telegram video validation requires >100KB and readable frames
6. **Hard-coded Thresholds**: Many magic numbers scattered across detection.py
7. **Single Camera**: No multi-camera support in main pipeline
8. **No Health Checks**: No component-level health reporting

---

## 10. Reusable Functions / Classes

| Component | Source | Reusable? |
|-----------|--------|-----------|
| YOLO detection | detection.py::detect_people() | Yes - wrap in detector |
| MediaPipe pose | detection.py::estimate_pose() | Yes - wrap in pose_estimator |
| Feature extraction | feature_extractor.py::PoseFeatureExtractor | Yes - wrap in feature_extractor |
| SimpleTracker | tracking.py::SimpleTracker | Yes - wrap in tracker |
| Sequence features | sequence_features.py | Yes - wrap in temporal_buffer |
| GRU inference | action_sequence_classifier.py | Yes - wrap in gru_adapter |
| Legacy MLP | action_classifier.py | Yes - as fallback |
| Video clipper | video_clipper.py | Yes - wrap in evidence_clipper |
| Rule-based detection | detection.py::LocalSafetyAnalyzer | Yes - as fallback |

---

## 11. Duplicate Code

1. **YOLO Loading**: Loaded twice (detection.py + feature_extractor.py) - should share instance
2. **MediaPipe Pose**: Initialized in both detection.py and feature_extractor.py
3. **Person Detection**: Duplicate logic in detect_people() methods
4. **Configuration**: Hard-coded in multiple files

---

## 12. Missing Components (Need Implementation)

1. **Video Source Abstraction**: Unified interface for file/webcam/RTSP/DroidCam
2. **Configuration System**: Centralized YAML/env config
3. **Async Frame Processing**: Non-blocking pipeline
4. **Health Monitoring**: Per-component status
5. **Error Recovery**: Graceful degradation modes
6. **Structured Output**: Normalized agent output schema
7. **Agent Interface**: BaseAgent integration
8. **Tests**: Unit + integration tests
9. **Visualization**: Debug overlay (optional)

---

## 13. Recommended Integration Strategy

### Phase 1: Core Adapters (Wrap Existing)
1. yolo_adapter.py - Wrap Ultralytics YOLO with config
2. mediapipe_adapter.py - Wrap MediaPipe pose with config
3. gru_adapter.py - Wrap ActionSequenceClassifier with config
4. tracker.py - Wrap SimpleTracker

### Phase 2: Pipeline Components
1. video_source.py - Abstract video input with reconnect
2. frame_processor.py - Coordinate detector -> tracker -> pose
3. temporal_buffer.py - Rolling sequence buffer per track
4. activity_classifier.py - Combine GRU + rule-based fallback

### Phase 3: Vision Agent
1. agent.py - BaseAgent implementation
2. schemas.py - Output schemas
3. config.py - Centralized configuration
4. Health checks + error handling

### Phase 4: Testing
1. Unit tests for each adapter
2. Integration test: video -> output
3. Real camera test
4. Performance benchmarks
