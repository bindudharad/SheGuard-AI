# Migration Report

## Summary

The FastAPI backend was extracted from `C:\Programs\codex\SheGuard\SheGuard_AI` into `C:\Programs\codex\SheGuard\SheGuard_Backend` as a standalone `app` package. The AI CCTV runtime remains in `SheGuard_AI` with model artifacts, YOLO/MediaPipe logic, classifiers, datasets, evidence generation, video processing, and training scripts preserved.

## Backend Files Migrated

- `backend/api/*` -> `app/api/*`
- `backend/routes/*` -> `app/routes/*`
- `backend/database/*` -> `app/database/*`
- `backend/models/*` -> `app/models/*`
- `backend/services/*` -> `app/services/*`
- `logging_config.py` -> `app/core/logging_config.py`
- `.env`, `config.yaml`, `sheguard.db`, `groq_client.py` copied into backend root
- Backend test copied and updated under `tests/test_backend.py`
- Legacy backend package moved to `migration_sources/legacy_backend_package` for recovery/audit only

## AI Files Kept In AI

- `main.py`
- `action_classifier.py`
- `action_sequence_classifier.py`
- `utils/*`
- `train.py`, `train_v2.py`, `predict.py`
- `dataset/*`, `data/*`, `models/*`, `raw_videos/*`
- `evidence/*`, `captures/*`, `clips/*`
- `yolov8n.pt` and local model artifacts

## Validation

- `python -m compileall app tests -q` passed.
- `python -m compileall main.py services utils action_classifier.py action_sequence_classifier.py train.py train_v2.py predict.py -q` passed.
- `python -m pytest tests -q` passed in `SheGuard_Backend`.
- `uvicorn app.main:app --host 127.0.0.1 --port 8000` answered `GET /` with `{"status":"ok","service":"SheGuard Backend","version":"2.0.0"}`.

## Notes

- No AI models, datasets, captures, clips, raw videos, or training artifacts were moved out of `SheGuard_AI`.
- The old backend package was moved, not silently deleted, and remains available in `SheGuard_Backend/migration_sources`.
