# SheGuard AI / Model Test Report

**Generated:** 2026-08-07 · **Mode:** read-only inference verification, CPU-only.

---

## 1. Models verified

### Legacy RandomForest pipeline (`SheGuard\`)
| Artifact | File | Load | Notes |
|---|---|---|---|
| Classifier | `model.joblib` | ✅ | classes: attack, fall, fight, normal |
| Scaler | `scaler.joblib` | ✅ | |
| Label encoder | `label_encoder.joblib` | ✅ | |
| Pose features | `utils/feature_extractor.py` → `feature_length()` | ✅ | **108 features** |
| Sample inference | random sample | ✅ | → `fight` conf 0.627, 205 ms |

Training data was tiny: **59 samples** (attack 5, fall 10, fight 39, normal 5) → heavy class imbalance.
This explains weak generalization.

### GRU sequence model v2 (`SheGuard\models\v2\`)
| Artifact | File | Load | Notes |
|---|---|---|---|
| Checkpoint | `sheguard_sequence_model.pt` (815 KB) | ✅ | 16-frame sequences |
| Scaler | `sequence_scaler.joblib` | ✅ | |
| Label encoder | `sequence_label_encoder.joblib` | ✅ | classes: attack, fall, fight, normal |
| Feature length | — | — | **116 features** |
| Reported metrics | `metrics.json` / `metrics_v2.json` | ✅ | test acc **0.8538**, macro-F1 0.8538, per-class: fall .90 / fight .89 / normal .86 / **attack .77** |

> `metrics.json` and `metrics_v2.json` are byte-identical duplicates (5,478 B each).

## 2. Real-video inference (CPU)

| Video | Classifier | Frames | Wall time | Effective FPS | Frame cost | Predictions |
|---|---|---|---|---|---|---|
| `V_1.mp4` (attack, 1080p @15fps) | legacy | 15 | 5.9 s | 2.56 fps | 261 ms/frame | **all 15 → "fight"** (attack misclassified) |
| `NV_1.mp4` (normal) | GRU | 40 | 4.7 s | 8.45 fps | — | **{fight: 31, normal: 2}** — extreme false positives |

### Key discrepancy
- Offline test metrics (0.85 accuracy) **do not transfer to real footage**:
  - Attack clip is labeled `fight` on every frame.
  - A normal (non-violent) clip is labeled `fight` in 31/33 frames → would trigger false alarms continuously.
- Root causes to investigate: training/validation leakage on processed synthetic sequences, class imbalance
  in the legacy set, frame-rate mismatch (2.56 fps is below a typical 15-30 fps expectation), and no
  temporal smoothing/thresholding before alerting.

## 3. Pipeline components

| Component | Status |
|---|---|
| YOLOv8n person detection (`yolov8n.pt`, 6.5 MB) | ✅ loads, runs |
| MediaPipe pose estimation | ✅ init OK (deprecation warnings only) |
| Action classifier (frame) | ✅ legacy path |
| Action sequence classifier (GRU) | ✅ v2 path |
| Alert path (Groq/Gemini/Telegram) | ⚠️ not exercised live; old `sheguard.log` shows Telegram timeouts |

## 4. Dataset

| Class | Files | Size |
|---|---|---|
| attack | 243,859 | 1,874.5 MB |
| fall | 26,197 | 2,206.2 MB |
| fight | 527 | 31.2 MB |
| raw_videos | 1,000 attack + 1,000 normal | (videos) |
| processed pose sequences | `processed/sequences/*.npz` | very large |

Huge imbalance (attack files massively over-counted vs. fight). V2 training used balanced 798/class sequences.

## 5. Verdict

- **Model loading & inference: ✅ operational** (CPU).
- **Real-world accuracy: ⚠️ poor** — attack→fight and normal→fight errors; not production-safe without
  retraining on balanced real data + post-processing smoothing.
- **Throughput: ⚠️ 2.6–8.5 fps on CPU** — below real-time for HD streams; CUDA build would help.

**AI engine score: 6 / 10**
