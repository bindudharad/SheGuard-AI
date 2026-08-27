# SheGuard Existing AI Inventory

**Date**: 2026-08-18
**Component**: SheGuard_AI (and AI-related pieces in SheGuard_Backend)
**Purpose**: Catalog every AI/ML model, pipeline, and inference component, with reuse recommendation for SheGuard_agents.

---

## 1. Object Detection — YOLOv8n
- **File**: `SheGuard_AI/yolov8n.pt` (6,549,796 bytes)
- **Library**: `ultralytics` YOLOv8 nano
- **Task**: Person detection (COCO class 0)
- **Used in**: `utils/detection.py::LocalSafetyAnalyzer.detect_people()` (conf 0.45); `utils/feature_extractor.py::PoseFeatureExtractor.detect_people()` (conf 0.35)
- **Reuse**: **DIRECT** — wrap in Vision Agent detector.

## 2. Pose Estimation — MediaPipe Pose
- **Library**: `mediapipe.solutions.pose`
- **Complexity**: 1 (balanced); static_image_mode False; min detection/tracking conf 0.45; 33 landmarks
- **Key landmarks**: NOSE(0), L/R SHOULDER(11/12), L/R ELBOW(13/14), L/R HIP(23/24), L/R KNEE(25/26), L/R ANKLE(27/28)
- **Used in**: `utils/detection.py::estimate_pose()`; `utils/feature_extractor.py::extract_from_image()`
- **Reuse**: **DIRECT** — wrap in Vision Agent pose module.

## 3. Tracking — SimpleTracker (centroid-based)
- **File**: `SheGuard_AI/utils/tracking.py`
- **State**: `PersonTrack` (track_id, bbox, center, last_center, speed, pose, fall_counter, still_since, last_head_hip_delta)
- **Algo**: nearest-centroid match (max 120px, stale 1.5s)
- **Reuse**: **DIRECT** — wrap as Vision Agent tracker.

## 4. Rule-Based Detection (`utils/detection.py::LocalSafetyAnalyzer`)
| Signal | Logic | Persistence | Confidence |
|--------|-------|-------------|------------|
| Fall | head below hip+20px OR sudden drop >45px OR lying shape (w>h*1.15) | 6 frames | 0.90 |
| Unconscious | keypoint move <8px AND center move <10px for 5s | once per still | 0.85 |
| Attack | 2+ persons, dist <170px, speed >32px/frame, moving toward each other | 8 frames | 0.80 |
- **Reuse**: **WRAP** as Vision Agent rule-based fallback (neutral labeling: "possible confrontation", "possible physical aggression", not "criminal").

## 5. Legacy ML Classifier — scikit-learn MLP
- **Files**: `models/model.joblib` (678,873 B) + `scaler.joblib` (3,207 B) + `label_encoder.joblib` (423 B)
- **Features** (`utils/feature_extractor.py`): normalized keypoints (33*2) + visibility (33) + body angles (6) + temporal (speed, posture_ratio, inactivity) = 138
- **Labels**: fall, attack, fight, normal; threshold 0.75
- **Quality**: **POOR** (~0.75 acc, attack/normal precision 0.0). **Reuse only as backstop**, never as primary.

## 6. Temporal Sequence Classifier — PyTorch GRU (PRIMARY temporal)
- **Files**: `models/v2/sheguard_sequence_model.pt` + `sequence_scaler.joblib` + `sequence_label_encoder.joblib`
- **Arch**: 2-layer GRU + LayerNorm/Linear head. Hidden size from checkpoint. Input size 116 (= 108 pose/visibility/angle + 8 optical-flow motion). Sequence length 16. Classes: attack/fall/fight/normal.
- **Quality**: **VALID** — test accuracy 85.4%, macro-F1 0.854 (attack 0.77, fall 0.90, fight 0.89, normal 0.86).
- **Logic** (`action_sequence_classifier.py`): per-track feature history, pad/trim, scaler, GRU forward, smoothing (majority + prob avg), persistence 3 frames, trigger 0.72 / clear 0.52, stale-track drop (3s).
- **Note**: loads checkpoint with `weights_only=False` (required for this dict); reloads a local `SequenceGRU` class def (must match dims). Silent-disable if torch missing.
- **Reuse**: **WRAP** as Vision Agent temporal module (do NOT retrain). Clearly mark DEMO if model files absent.

## 7. Cloud AI — Groq Vision (`SheGuard_AI/groq_client.py::GroqVisionClient`)
- **Model**: `meta-llama/llama-4-scout-17b-16e-instruct` (env `GROQ_VISION_MODEL`)
- **Trigger**: after local detection event
- **I/O**: base64 JPEG + prompt → `GroqAnalysis(description, confirms_danger, severity, model, error)`
- **Danger**: keyword heuristic (danger/injured/fallen/attack/assault/distress/help) minus denials. Errors swallowed.
- **Reuse**: pattern → "Safety Intelligence Service" (x402 target). Danger heuristic needs improvement; not authoritative.

## 8. Cloud AI Orchestrator — Backend (`SheGuard_Backend/app/services/cloud_ai.py`)
- **Priority**: Groq → Gemini (`gemini-1.5-flash`) → OpenRouter (`openai/gpt-4o-mini`) → local fallback
- **Safety gate**: event in {fall,fight,attack,unconscious,dragging,forced_movement,weapon} AND (conf ≥0.78 OR threat ≥5)
- **EmbeddingClient**: NVIDIA/HF text embeddings, deterministic hash fallback (for incident memory search)
- **Reuse**: reference for x402 service design + Context Agent history search. **Not x402/paid** — free LLM only.

## 9. Video Processing
- **Capture**: DroidCam (idx 1/2, reconnect), RTSP, video file, USB cam; configurable frame_skip
- **Evidence clip**: `video_clipper.py::EventClipBuffer` rolling deque (150 frames) → MP4 (`mp4v`)
- **Reuse**: **DIRECT** evidence rolling buffer (add SHA-256 + retention + pre/post window).

## 10. Model File Inventory
| File | Size | Type | Required for |
|------|------|------|--------------|
| `yolov8n.pt` | 6.5 MB | Ultralytics | all detection |
| `models/model.joblib` | 679 KB | sklearn MLP | legacy backstop |
| `models/scaler.joblib` | 3.2 KB | sklearn | legacy backstop |
| `models/label_encoder` | 423 B | sklearn | legacy backstop |
| `models/v2/sheguard_sequence_model.pt` | ~? | PyTorch GRU | temporal (primary) |
| `models/v2/sequence_scaler.joblib` | — | sklearn | temporal |
| `models/v2/sequence_label_encoder.joblib` | — | sklearn | temporal |
| `pose_features.npz` | 20 KB | numpy | training reference |

## 11. Reuse Mapping
| SheGuard_agents component | Existing code | Approach |
|---------------------------|---------------|----------|
| `agents/vision/detector.py` | `utils/detection.py::detect_people()` | direct wrap |
| `agents/vision/pose.py` | `utils/detection.py::estimate_pose()` | direct wrap |
| `agents/vision/tracker.py` | `utils/tracking.py::SimpleTracker` | direct wrap |
| `agents/vision/temporal.py` | `action_sequence_classifier.py` + `utils/sequence_features.py` | direct wrap (GRU) |
| `agents/vision/activity_classifier.py` | `LocalSafetyAnalyzer` rules + `ActionClassifier` | wrap as rule/backstop |
| `agents/response/evidence.py` | `video_clipper.py` + backend `evidence_manager.py` | wrap + SHA/retention |
| `services/safety_intelligence/` | `groq_client.py`, `cloud_ai.py` | refactor as x402 service |

## 12. Missing for production
1. GRU model validation on load (assert classes/dims).
2. Confidence calibration (raw probs used).
3. Bias audit (pose/detection across demographics).
4. The backend `.env` live secrets must NOT be reused (see `EXISTING_SYSTEM_AUDIT.md` §1).
