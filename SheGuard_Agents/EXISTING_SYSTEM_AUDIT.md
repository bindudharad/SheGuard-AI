# SheGuard Existing System Audit

**Date**: 2026-08-18
**Auditor**: SheGuard AI+ Autonomous Agent System (Phase 1 read-only audit)
**Scope**: Complete audit of the four existing SheGuard components, plus the partial `SheGuard_agents` scaffold already present in the repo, to determine what to reuse, wrap, or rewrite for the new autonomous multi-agent safety layer.

> This audit is READ-ONLY with respect to the legacy components (`SheGuard_AI`, `SheGuard_Backend`, `SheGuard_App`, `SheGuard_Dashboard`). Nothing in those four folders was modified. The only files touched inside `SheGuard_agents` were two prototype core modules (`core/agent.py`, `core/event_bus.py`) whose Python source was corrupted (escaped-quote literals) — those were repaired so the new layer can build on them.

---

## 1. Executive Summary

The existing SheGuard project is a **detector → alert pipeline**, not an agent system. It has strong, already-trained vision/temporal/notification pieces that we should *wrap*, and a mature FastAPI/SQLite backend we should *reference* — but it lacks the agent infrastructure the master prompt requires (Event Bus, Risk Engine, Decision Agent with uncertainty reasoning, x402 Agent, Algorand payment, Response/Incident orchestration, explainability trace).

| Component | Role | Reuse verdict |
|-----------|------|---------------|
| `SheGuard_AI` | CV/ML pipeline (YOLOv8 + MediaPipe + GRU) | **WRAP** as Vision Agent |
| `SheGuard_Backend` | FastAPI + SQLite + Telegram + incident/evidence storage | **REFERENCE** (do not depend on; new API is independent) |
| `SheGuard_App` | Flutter mobile (APK currently unreliable) | **NOT A BLOCKER** (Phase 2/3) |
| `SheGuard_Dashboard` | React/Vite polling dashboard | **CONSUME LATER** (Phase 9) |
| `SheGuard_agents` | New target dir (partial scaffold present) | **BUILD HERE** |

### Critical security finding (must fix before any reuse)
The committed `SheGuard_Backend/.env` contains **real, live secrets**:
- `GROQ_API_KEY=gsk_...`
- `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `HF_API_KEY`, `NVIDIA_API_KEY`
- `TELEGRAM_BOT_TOKEN=8906267843:...` and `TELEGRAM_CHAT_ID=5709004610`
- `SHEGUARD_SERVICE_TOKEN=sheguard-ai-service-token-2026`

These must **never** be copied into `SheGuard_agents/.env`. Use `.env.example` (placeholders only). Recommend rotating these tokens in the legacy project. The legacy `.env.example` files are already safe (no secrets).

---

## 2. SheGuard_AI — Computer Vision & ML Pipeline

**Entry point**: `SheGuard_AI/main.py` → `HybridSafetySystem` (single-process live loop).
**Pipeline**: OpenCV frame capture → YOLOv8 person detection → MediaPipe pose (33 landmarks) → centroid tracking → rule-based + optional ML → Groq cloud vision → backend alert.

### 2.1 AI Models (what exists, what works)
| Model | Path | Type | Status | Notes |
|-------|------|------|--------|-------|
| YOLOv8n | `SheGuard_AI/yolov8n.pt` (6.5 MB) | Ultralytics object detection | **Working** | Person detection (COCO class 0), confidence 0.45 |
| MediaPipe Pose | built-in | Pose estimation | **Working** | 33 landmarks, complexity 1 |
| Legacy MLP classifier | `models/model.joblib` + `scaler.joblib` + `label_encoder.joblib` | scikit-learn MLP | **Weak/Poor** | Reported ~0.75 accuracy, attack/normal precision 0.0; only a backstop |
| GRU temporal classifier | `models/v2/sheguard_sequence_model.pt` + scaler + label encoder | PyTorch 2-layer GRU | **Working (valid)** | Test accuracy 85.4%, macro-F1 0.854; classes: attack/fall/fight/normal; 16-frame sequence; feature length 116 |

### 2.2 Detection capabilities (`utils/detection.py::LocalSafetyAnalyzer`)
- **Fall**: head-hip delta, sudden drop >45px, lying-shape ratio; 6-frame persistence; fixed confidence 0.90.
- **Unconscious/no-movement**: 5s stillness, keypoint movement <8px; confidence 0.85.
- **Attack**: 2+ persons, distance <170px, speed >32px/frame, moving toward each other; 8-frame persistence; confidence 0.80.

### 2.3 Cloud AI (`groq_client.py`, `action_sequence_classifier.py`)
- `GroqVisionClient.analyze_image()` sends event frame (base64) to Groq vision; danger = keyword heuristic (`danger`, `attack`, `help`, …) minus denials. Errors swallowed into a `GroqAnalysis`.
- `ActionSequenceClassifier` is a solid temporal engine: per-track feature history, pad/trim, smoothing (majority + prob averaging), persistence 3 frames, trigger 0.72 / clear 0.52. **This is the temporal component we wrap, not rebuild.**

### 2.4 Video input & evidence (`video_clipper.py::EventClipBuffer`)
- Sources: DroidCam indices 1/2 (auto-reconnect), RTSP, video file, USB cam.
- Rolling `deque` frame buffer (default 150 frames ≈ 7.5s @20fps) → MP4 on event via `cv2.VideoWriter` (`mp4v`).
- **Gaps**: no configurable pre/post window (fixed 150), no SHA-256, no retention policy, `mp4v` can silently fail to open.

### 2.5 Output format
`SafetyEvent(event_type, display_text, confidence, message)` → JSON alert payload POSTed to `http://127.0.0.1:8000/incidents/create`.

### 2.6 What is BROKEN / unreliable
- `main.py` is **DroidCam-only**, sync, no event bus, no confidence fusion, hardcoded backend URL.
- Legacy MLP accuracy too poor to trust.
- Groq danger detection is naive keyword matching; API key never validated at init.
- No incident/risk/trace DB schema.
- No x402 / Algorand / payment layer.

---

## 3. SheGuard_Backend — FastAPI Backend

**Entry**: `uvicorn app.main:app` (v2.0.0). SQLite + SQLAlchemy 2.0, CORS configurable (`SHEGUARD_CORS_ORIGINS`, default `*`), mounts `/uploads`, startup runs DB init + incident watchdog.

### 3.1 Database (SQLAlchemy 2.0, `app/models/entities.py`)
11 tables: `users`, `emergency_contacts`, `live_locations`, `tracking_sessions`, `incidents`, `evidence`, `incident_victim_links`, `emergency_sessions`, `emergency_notifications`, `evidence_records`, `cctv_cameras`. `init_database()` performs legacy migrations + column/add-index migrations on startup.

### 3.2 Risk / threat logic (`app/services/advanced_threat.py`)
Transparent **additive** scoring on a **0–10** scale (note: spec wants 0–100):
- fall +3.5, fight/attack +5.5, unconscious +3.0; confidence ≥0.90 +2.0, ≥0.75 +1.0; inactivity/inactivity; motion anomaly +1.3; nighttime (20:00–05:00) +1.0; kidnap suspicion from dragging/resistance/route changes.
- `threat_level()`: ≥9 CRITICAL, ≥7 HIGH, ≥4 MEDIUM, else LOW. `explain_detection()` returns reasons. **This is the right pattern for our RiskEngine** (but we make weights configurable in YAML and rescale to 0–100).

### 3.3 Telegram integration (`app/services/telegram_service.py`)
Sends message → photo → video → location via Bot API. Validates video (>100KB, re-readable), 120s timeout. **Reuse logic, but remove the many leftover `print()` debug statements** that leak absolute paths.

### 3.4 Evidence storage (`app/services/evidence_manager.py`, `media_storage.py`)
`RollingVideoBuffer` (pre-event ring) + `save_detection_evidence()` → per-incident folder under `uploads/incidents/incident_<ts>/` (frame, video, thumbnail, metadata.json). Path-traversal guard (`safe_incident_id`). Retention configured in `config.yaml`. **Very high reuse value** for the Evidence Agent.

### 3.5 Realtime / WebSocket (`app/services/realtime.py` + `routes/realtime.py`)
In-memory `RealtimeHub`: `broadcast()`, `broadcast_session()`, `publish_from_sync()`. Endpoints: `WS /ws/live`, `WS /ws/emergency/{session_id}`, `WS /ws/tracking/{session_id}`. **Single-process only** (in-memory) — fine as a reference for our `/ws/events`.

### 3.6 Cloud AI (`app/services/cloud_ai.py`)
`CloudAIOrchestrator` (Groq → Gemini → OpenRouter → local). Free LLM calls; **this is the closest existing analog to the new "safety intelligence" service, but it is NOT x402/paid.**

### 3.7 What is BROKEN / risky
1. **Live secrets committed in `.env`** (see §1).
2. `telegram_service.py` `print()` noise leaks filesystem paths.
3. `advanced_detectors.py` modules (Weapon/Dragging/CrowdAggression) are **stubs returning no real signal**.
4. No YOLO/MediaPipe/GRU in backend (vision lives in `SheGuard_AI`).
5. In-memory WebSocket hub (not multi-worker safe).
6. Deprecated `@app.on_event("startup")`.
7. Risk scale is 0–10, not 0–100.

---

## 4. SheGuard_App — Flutter Mobile App

- Flutter/Dart, `provider` state, `http` REST, `web_socket_channel` for realtime.
- Features: live tracking, SOS (button/long-press/triple-tap/shake/fall), incident feed, contacts, encrypted evidence capture.
- **SOS path is FREE emergency response** — no payment gate (matches the master safety rule).
- API base URL hardcoded to `http://10.228.102.43:8000`.
- WS: `ws(s)://base/ws/live?user_id=&token=`, expects `incident.created` / `incident.merged` envelopes.
- **Status: NOT A BLOCKER.** The new agent system operates independently; mobile integration is Phase 2/3.

---

## 5. SheGuard_Dashboard — React/Vite

- React 18 + Vite, Tailwind, Framer Motion, Leaflet maps, Recharts, axios.
- Pages: `LoginPage`, `DashboardPage` (2s polling), `IncidentDetailPage`.
- **No WebSocket** — purely polling (`REFRESH_INTERVAL_MS=2000`). Base URL `http://10.228.102.43:8000`.
- Consumes `/incidents`, `/incidents/latest`, `/incidents/{id}`, `/tracking/live/{sessionId}`, `/location/live/{userId}`. `normalizeIncident()` tolerates many field aliases and 0–1/0–100 confidence.
- **Status**: resilient polished viewer; no concept of agents, risk levels, x402, payments, or decision traces — those are net-new.

---

## 6. SheGuard_agents — Existing partial scaffold (audited)

A partial scaffold already exists in this directory. Findings:
- **`core/agent.py` & `core/event_bus.py`** contained corrupted Python (escaped `\"` literals) and would not import. **Repaired in this audit** to valid syntax (same design: `AgentStatus`, `AgentHealth`, `AgentMessage`, `BaseAgent`, `EventBus`, `AgentRegistry`).
- `agents/vision/` has a fairly complete prototype (agent, config, schemas, pipeline modules: detector, tracker, pose_estimator, temporal_buffer, activity_classifier, interaction_detector) — but it imports the broken `core` and the `_gen_*.py` / `_gen_*.json` files at the repo root are stray generation artifacts, **not** part of a clean architecture.
- `agents/context/` has analyzers + providers. `agents/audio/` has models/pipeline/tests stubs.
- **No** `core/agent_state.py`, `core/agent_registry.py` (registry currently lives in `event_bus.py`), `core/message.py`, `core/orchestrator.py`, `core/pipeline.py`, `core/confidence.py`, `core/risk_engine.py`, `core/exceptions.py`.
- No API, no simulation, no tests beyond stubs.

**Decision**: Keep the good prototype code as reference, but the master prompt's target structure is the authoritative plan. We will build `core/` properly (separating agent_state/message/registry), implement the agents per the spec, and treat the existing vision prototype as a *starting point to refactor*, not a finished product.

---

## 7. Integration Map (current → new)

```
SheGuard_AI ──POST /incidents/create──▶ SheGuard_Backend ──Telegram──▶ Guardian
                                          │
                                          ├─SQLite (incidents/evidence)
                                          ├─WS /ws/live──▶ Dashboard (polling) / App (WS)
                                          └─Cloud AI (Groq/Gemini/OpenRouter)

SheGuard_agents (NEW, independent):
  Vision ─▶ Threat ─▶ Decision ─▶ (x402 ─▶ Algorand) ─▶ Response
        │                                                    │
        └── Event Bus ──▶ /ws/events ──▶ Dashboard (later) ──┘
```

---

## 8. Answers to the 15 audit questions

1. **Existing AI to reuse?** YOLOv8n detection, MediaPipe pose, GRU temporal classifier (valid, 85% acc), Groq vision client pattern, EventClipBuffer, Telegram sender logic, `advanced_threat` scoring pattern, evidence rolling-buffer.
2. **Where is YOLO?** `SheGuard_AI/utils/detection.py::LocalSafetyAnalyzer.detect_people()` + `utils/feature_extractor.py`; `yolov8n.pt` at `SheGuard_AI/`.
3. **Where is MediaPipe?** `SheGuard_AI/utils/detection.py::estimate_pose()` and `utils/feature_extractor.py` (`mp.solutions.pose`).
4. **Where is GRU?** `SheGuard_AI/action_sequence_classifier.py` + `models/v2/sheguard_sequence_model.pt`.
5. **How is video processed?** `HybridSafetySystem.run()` OpenCV loop → frame → analyzer → classifier → Groq → alert.
6. **How are incidents generated?** `SheGuard_AI/main.py` posts to backend; backend `POST /incidents/create` creates `Incident` + `Evidence` + Telegram + realtime broadcast.
7. **How is evidence stored?** `SheGuard_Backend/app/services/evidence_manager.py` + `media_storage.py` → `uploads/incidents/<folder>/` with metadata.json + SHA-free retention.
8. **How are Telegram notifications sent?** `SheGuard_Backend/app/services/telegram_service.py::send_telegram_alert with TELEGRAM_BOT_TOKEN/CHAT_ID`.
9. **Existing backend endpoints?** 30+ (see `EXISTING_API_INVENTORY.md`): users, contacts, locations, incidents, evidence, emergency, notifications, cameras, realtime WS, system.
10. **Database used?** SQLite (`sheguard.db`), SQLAlchemy 2.0, 11 tables (see `EXISTING_DATABASE_INVENTORY.md`).
11. **Code NOT to duplicate?** `HybridSafetySystem` monolith, `incidents.py` complex merge logic, `advanced_threat.py` (replace with configurable RiskEngine), `realtime.py` (replace with Event Bus), `incident_memory.py` (replace with Context Agent).
12. **What is broken?** Live secrets in `.env`; DroidCam-only AI loop; weak legacy MLP; stub detectors; in-memory WS; 0–10 (not 0–100) risk; corrupted `SheGuard_agents/core/*.py` (now fixed).
13. **What can be wrapped as an agent?** Vision (YOLO+MediaPipe+GRU), Context (camera/zone/time/history providers), Audio (adapter+stub), Response (evidence+Telegram+camera).
14. **What must be rewritten?** Event Bus, Agent Registry (separated), Orchestrator, Risk Engine, Decision Agent, x402 Agent, Algorand wallet/payment, Safety Intelligence service, FastAPI layer, simulation/demo.
15. **What can remain independent?** `SheGuard_Backend`, `SheGuard_App`, `SheGuard_Dashboard` — the new `SheGuard_agents` API is a standalone system; the old backend is only a *reference*, not a dependency.

---

## 9. Proposed SheGuard_agents architecture (Phase 2+)

See `ARCHITECTURE.md` (to be created in Phase 2) and `REUSE_PLAN.md` (below). In short: independent FastAPI service + async Event Bus + 7 agents (vision, audio, context, threat, decision, x402, response) + safety-intelligence service + SQLite store + WebSocket `/ws/events` + simulation/demo harness.

---

## 10. Exact next implementation step (Phase 2)

Build `core/` properly and prove it works:
1. `core/exceptions.py` — agent exceptions.
2. `core/agent_state.py` — `AgentStatus` + `AgentHealth` (move out of `agent.py`).
3. `core/message.py` — `AgentMessage` + `Event` schema (move out of `event_bus.py`).
4. `core/agent.py` — `BaseAgent` (already repaired; align with new state/message modules).
5. `core/agent_registry.py` — standalone registry.
6. `core/event_bus.py` — pub/sub (already repaired; use `message.py` types).
7. `core/confidence.py` — confidence aggregation/calibration.
8. `core/risk_engine.py` — transparent weighted 0–100 scoring with YAML weights + explainability.
9. `core/orchestrator.py` — lifecycle, dispatch, incident state, retries, dedup.
10. `config/settings.py` + `config/thresholds.yaml` — settings + risk weights/thresholds.
11. Unit tests for `core/` (event bus, risk engine, base agent, registry).

Then move to Phase 3 (Vision/Threat/Decision/Response agents in simulation mode).
