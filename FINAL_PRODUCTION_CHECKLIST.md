# SheGuard Final Production Readiness Checklist

**Generated:** 2026-08-07 · Purpose: what must be done to take SheGuard to production.

Legend: ☐ pending · ✅ verified done · ⚠️ partial/needs action

---

## A. Secrets & Configuration

- ✅ `.env` is gitignored.
- ☐ **Set a real `SHEGUARD_JWT_SECRET`** (placeholder breaks auth — verified 500).
- ☐ Set a real admin password (currently `change-me`).
- ☐ Set `SHEGUARD_CORS_ORIGINS` to explicit dashboard origin(s), not `*`.
- ☐ Rotate the GROQ/GEMINI/OPENROUTER/HF/NVIDIA keys and Telegram token if the repo was ever shared.
- ☐ Consider disabling `/docs`, `/redoc`, `/openapi.json` in prod (or gate behind auth).

## B. Backend dependencies (2 installs unlock core features)

- ☐ `pip install python-multipart` → fixes `/incidents/create` 500.
- ☐ `pip install websockets` → enables `/ws/live`, `/ws/emergency`, `/ws/tracking`.
- ✅ FastAPI 0.136.1, uvicorn 0.46.0, SQLAlchemy 2.0.49 verified working.

## C. Backend code

- ☐ Add `/emergency/status` endpoint (Flutter polls it every 15 s).
- ☐ Fix route order: register `/evidence/file` before `/evidence/{incident_id}`.
- ☐ Add login rate limiting / account lockout.
- ☐ Add pagination to `/incidents` and `/incident/history`.
- ☐ Add upload size/type limits to evidence + media endpoints.
- ⚠️ Move the misplaced `groq_client.py` into `app/`; dedupe with `SheGuard\groq_client.py`.
- ⚠️ Remove orphaned `telegram_test.py`, `telegram_photo_test.py`, `telegram_video_test.py`, legacy `telegram.py`, `train_v2.py`.
- ⚠️ Decide fate of legacy `SheGuard\backend.py` + `SheGuard\sheguard.db` (two backends in repo).

## D. AI engine

- ☐ **Retrain / recalibrate models on balanced real footage** — verified: attack→"fight", normal→"fight" false positives.
- ☐ Add temporal smoothing/threshold before alerting.
- ☐ Ship CUDA build of torch or GPU host (2.6–8.5 fps CPU is below real-time).
- ☐ Validate alert path (Groq/Gemini/Telegram) end-to-end; old logs show Telegram timeouts.

## E. Dashboard

- ☐ Fix `normalizeIncident` title/address mapping (`incident_type` vs `type`).
- ☐ Make API base URL runtime-configurable; drop hardcoded `192.168.1.3`.
- ⚠️ 513 kB chunk — code-split if desired.
- ✅ Build + login + incidents verified working (rebuilt with `VITE_API_BASE_URL`).

## F. Flutter app

- ☐ **Install working JDK 17+** and rebuild APK (blocked: broken JAVA_HOME, no jlink.exe).
- ☐ Replace hardcoded `192.168.1.3:8000` in `lib/config/api_config.dart` with configurable/auto base URL.
- ✅ `flutter analyze` clean; 6/6 tests pass.
- ⚠️ Runtime on device/emulator not verifiable in this environment (no AVD/devices).
- ⚠️ Remove 7 unused files (app_routes, localhost, core/api_config, camera_service, metric_tile, status_tile, timeline_card).

## G. Database

- ✅ Integrity OK, 0 FK violations, 16 tables, 40 indexes.
- ⚠️ Backfill incident→user links (98/174 NULL) and evidence (97/174 NULL) if needed for analytics.
- ⚠️ Move to Postgres for multi-worker production.

## H. Realtime / streaming

- ✅ REST tracking/location streams verified.
- ☐ WebSocket layer must be enabled (dep §B) and end-to-end tested.

## I. Monitoring & ops

- ☐ Reduce watchdog 1 s log spam (`STEP 4 COOLDOWN CHECK`).
- ☐ Add health-check path `/health` (currently only `/`).
- ☐ Restart-safe process management (backend dies with `forrtl: error 200` when console closes — use service/wrapper).
- ☐ Gitignore large artifacts: `SHEGUARD_FULL_FILE_TREE.txt` (238 MB), `SheGuard/reports/*.json` (~187 MB), model `*.joblib`/`*.pt`, `SheGuard/sheguard.db`.

## J. Final gate

- ☐ End-to-end smoke: camera → YOLO → pose → classifier → `/incidents/create` (multipart) → DB → Telegram/Groq → dashboard/Flutter live view.
- ☐ Re-run full QA suite after fixes (this report set).

---

**Readiness summary:** REST core is production-plausible after config fixes; realtime, multipart uploads,
Android build, and AI accuracy are the four gate items blocking "production-ready".

