# SheGuard — README & Technical Claim Verification Report

**Document Date:** 2026-11-17  
**Project Path:** `C:\Programs\codex\SheGuard`  
**Primary Deliverable:** `C:\Programs\codex\SheGuard\README.md`  
**Verification Scope:** Complete multi-component ecosystem (App, Backend, AI, Agents, Dashboard)

---

## 1. Executive Summary

This verification report certifies that the newly created root-level [README.md](file:///C:/Programs/codex/SheGuard/README.md) for the **SheGuard** repository was composed following rigorous, empirical inspection of the actual codebase, dependency manifests, configuration templates, database schemas, cryptographic routines, and test suites across all five major subsystems.

**Core Verification Findings:**
* **Zero Fabrication**: Every documented API route, database entity, command-line argument, agent role, and classification label directly corresponds to verified source code.
* **No Unverified Marketing Claims**: The documentation strictly avoids unsubstantiated crime statistics, claims of 100% violence prevention, or exaggerations of production readiness.
* **Accurate Cryptographic Designation**: The evidence security system is documented as its actual implemented construction (**X25519-HKDF-AES256GCM** envelope encryption with a versioned key-ring and tamper-evident SHA-256 hash-chain ledger), explicitly clarifying that it is not RFC 9180 HPKE.
* **Source Code Preservation**: No working application code, database migrations, schemas, or logic were altered in the course of producing this documentation.

---

## 2. Modules & Key Source Files Inspected

| Module | Core Responsibility | Key Source Files Inspected |
| :--- | :--- | :--- |
| **SheGuard_App** | Flutter Mobile Application | • `pubspec.yaml` (dependencies, assets)<br/>• `lib/main.dart` (entry point)<br/>• `lib/config/api_config.dart` (`--dart-define` backend URLs)<br/>• `lib/services/sos_service.dart` (SOS orchestration)<br/>• `lib/services/voice_help_service.dart` (`speech_to_text` `"HELP"` detection)<br/>• `lib/services/motion_protection_service.dart` (`sensors_plus` shake detection)<br/>• `lib/services/location_service.dart` (`geolocator` GPS stream)<br/>• `lib/screens/fake_call_screen.dart` (simulated call)<br/>• `lib/services/evidence_capture_service.dart` (camera/mic evidence capture) |
| **SheGuard_Backend**| FastAPI Core Gateway & Persistence | • `app/main.py` (FastAPI app, CORS, routes mount)<br/>• `app/database/session.py` (SQLite WAL mode & `PRAGMA foreign_keys=ON`)<br/>• `app/models/entities.py` (12 declarative SQLAlchemy entities)<br/>• `app/services/crypto_service.py` (`EvidenceKeyRing`, X25519, AES-256-GCM)<br/>• `app/services/audit_service.py` (deterministic SHA-256 hash-chain ledger)<br/>• `app/services/realtime.py` (in-memory WebSocket hub)<br/>• `app/services/telegram_service.py` (optional Telegram bot alerts)<br/>• `app/routes/*.py` (incidents, emergency, locations, realtime, users, cameras) |
| **SheGuard_AI** | Computer Vision & Edge Analytics | • `requirements.txt` (OpenCV, YOLOv8, MediaPipe, Scikit-learn, PyTorch)<br/>• `main.py` (`HybridSafetySystem`, CLI flags, frame loop)<br/>• `action_classifier.py` (pose feature extraction and inference)<br/>• `label_encoder.joblib` (verified classes: `attack`, `fall`, `fight`, `normal`)<br/>• `yolov8n.pt` (Ultralytics nano model checkpoint)<br/>• `video_clipper.py` (pre/post incident video ring-buffer)<br/>• `utils/feature_extractor.py` (MediaPipe 33 landmarks + Farneback flow) |
| **SheGuard_Agents** | Multi-Agent Response Orchestration | • `core/orchestrator.py` (`Orchestrator`, agent lifecycle, incident states)<br/>• `core/event_bus.py` (AsyncIO publish-subscribe bus)<br/>• `agents/vision/agent.py` (`VisionAgent` — proximity, motion cues)<br/>• `agents/audio/agent.py` (`AudioAgent` — acoustic distress, VAD)<br/>• `agents/context/agent.py` (`ContextAgent` — spatial & temporal zone risk)<br/>• `agents/threat/agent.py` (`ThreatAgent` — multi-modal threat fusion)<br/>• `agents/decision/agent.py` (`DecisionAgent` — escalation heuristics)<br/>• `agents/response/agent.py` (`ResponseAgent` — automated alert dispatching)<br/>• `emergency/ws_client.py` (`LiveEventClient` WebSocket connection) |
| **SheGuard_Dashboard**| React 18 + Vite Tactical Command | • `package.json` (React 18.3.1, Vite 5.4.11, Leaflet 1.9.4, Tailwind 3.4.16)<br/>• `src/config.js` (`API_BASE_URL`, `WS_BASE_URL`, `REALTIME_EVENTS`)<br/>• `src/pages/DashboardPage.jsx` (live triage board)<br/>• `src/pages/TrackingPage.jsx` (real-time Leaflet GPS tracking)<br/>• `src/pages/EvidencePage.jsx` (authenticated evidence vault)<br/>• `src/pages/IncidentDetailPage.jsx` (investigation and timeline)<br/>• `src/hooks/useRealtime.js` (WebSocket auto-reconnect and dispatching) |

---

## 3. Verified Technical Claims & Architectural Facts

### 3.1 Cryptographic Evidence Architecture
* **Algorithm Verified**: Custom envelope encryption using `X25519` for ECDH key agreement, `HKDF-SHA256` for key derivation, and `AES-256-GCM` with a 96-bit random nonce for authenticated payload encryption.
* **Key-Ring Isolation Verified**: `EvidenceKeyRing` in `crypto_service.py` stores master keys exclusively in `~/.sheguard/keys/` with restrictive permissions. Key entries are managed with statuses `active`, `decrypt_only`, or `revoked`.
* **Audit Ledger Verified**: `audit_service.py` calculates a sequential SHA-256 hash over canonical fields starting from genesis hash (`"0" * 64`), providing verifiable **tamper-evidence** for all evidence access events.
* **Accuracy Requirement Met**: The README explicitly notes that this is an engineered custom envelope construction, not an RFC 9180 HPKE standard implementation, and that hash-chain auditing is tamper-evident rather than unbreakable.

### 3.2 Database Configuration & Safety
* **Database Engine**: SQLite via SQLAlchemy 2.0 (PostgreSQL compatible).
* **Concurrency Primitives**: `configure_sqlite_wal()` safely transitions SQLite to Write-Ahead Logging (`PRAGMA journal_mode=WAL`) outside active transactions.
* **Constraint Safety**: Connection listener executes `PRAGMA foreign_keys=ON` on every SQLite connection.
* **Schema Evolution**: `_ensure_sqlite_columns()` dynamically verifies table schemas and applies non-destructive column additions and indexes.

### 3.3 AI Classification & Computer Vision
* **Object Detector**: Ultralytics YOLOv8 nano (`yolov8n.pt`) identifying human bounding boxes.
* **Pose Extractor**: Google MediaPipe extracting 33 3D skeletal landmark coordinates.
* **Verified Classification Labels**: Ingested and verified directly from `SheGuard_AI/label_encoder.joblib`:
  1. `attack`
  2. `fall`
  3. `fight`
  4. `normal`
* **Evidence Buffering**: `video_clipper.py` maintains an in-memory frame ring-buffer, packaging 5-second video clips around triggered alarms.

### 3.4 Multi-Agent Collective
* **Agent Count & Roles**: Verified that `SheGuard_Agents` implements exactly 6 specialized agents:
  1. `VisionAgent`
  2. `AudioAgent`
  3. `ContextAgent`
  4. `ThreatAgent`
  5. `DecisionAgent`
  6. `ResponseAgent`
* **Communication Bus**: AsyncIO in-memory event bus (`core.event_bus.event_bus`) with decoupled publisher/subscriber queues.
* **Incident Lifecycle**: States verified as `NEW`, `MONITORING`, `ELEVATED`, `HIGH_RISK`, `CRITICAL`, `RESOLVED`, `FALSE_POSITIVE`.

### 3.5 Mobile Application Capabilities
* **SOS Trigger Modes**:
  1. One-tap tactile SOS button (`widgets/sos_button.dart`).
  2. Spoken distress keyword `"HELP"` via `speech_to_text` (`voice_help_service.dart`).
  3. Accelerometer motion shake threshold via `sensors_plus` (`motion_protection_service.dart`).
* **Live GPS**: Continuous location telemetry streaming via `geolocator`.
* **Fake Call Screen**: Realistic simulated incoming phone call (`fake_call_screen.dart`).
* **Evidence Capture**: Background audio and camera recording (`evidence_capture_service.dart`).

---

## 4. Verified Commands, Ports & URLs

| Component | Default Port | Primary URL / Endpoint | Verified Local Launch Command |
| :--- | :--- | :--- | :--- |
| **Backend API** | `8000` | `http://localhost:8000/docs` | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| **Backend WebSocket** | `8000` | `ws://localhost:8000/ws/live` | Handled internally by FastAPI ASGI server |
| **Command Dashboard**| `5173` | `http://localhost:5173` | `npm run dev` (inside `SheGuard_Dashboard`) |
| **Agent Server** | `8001` | `http://localhost:8001/docs` | `uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload` |
| **AI Vision Pipeline**| N/A | Local window / video stream | `python main.py --source 0 --backend-url http://127.0.0.1:8000/incidents/create` |
| **Flutter Web Preview**| Dynamic | Browser window | `flutter run -d chrome --dart-define=SHEGUARD_API_BASE_URL=http://localhost:8000` |
| **Flutter Android Emulator**| N/A | Virtual device display | `flutter run -d android --dart-define=SHEGUARD_API_BASE_URL=http://10.0.2.2:8000` |

---

## 5. Verified Automated Test Suites

| Module | Test Suite File | Command Executed | Result |
| :--- | :--- | :--- | :--- |
| **Backend** | `tests/test_phase4b_crypto.py` | `pytest tests/test_phase4b_crypto.py` | **6/6 Passed** |
| **Backend** | `tests/test_phase6b_keyring_audit.py` | `pytest tests/test_phase6b_keyring_audit.py` | **13/13 Passed** |
| **Backend** | `tests/test_phase3_db_hardening.py` | `python -m pytest tests/test_phase3_db_hardening.py` | **12/12 Passed** |
| **Agents** | `tests/test_phase2_ws_auth.py` | `python -m pytest tests/test_phase2_ws_auth.py -p no:asyncio` | **7/7 Passed** |
| **Dashboard**| Production Build Validation | `npm run build` | **Passed (Code 0, 2,113 modules transformed)** |
| **Mobile** | `test/widget_test.dart` | `flutter test` | **6/6 Passed** |
| **Mobile** | Static Analysis | `flutter analyze` | **1 error (`unawaited`), 19 warnings** (source code preserved per Rule 8) |

---

## 6. External Dependencies & Optional Integrations

The following items are optional or require dedicated external services/hardware:
1. **Telegram Alerts**: Fully implemented in `app/services/telegram_service.py`. Operates only when `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured in `.env`; otherwise gracefully bypasses alert dispatching without error.
2. **Groq Vision / LLM Summaries**: Implemented in `groq_client.py`. Generates natural-language risk explanations when `GROQ_API_KEY` is present; falls back to rule-based explanations if absent.
3. **Hardware Cameras / DroidCam**: `SheGuard_AI/main.py` defaults to camera index `0` (built-in webcam) or index `1`/`2` for DroidCam mobile camera links. Can also execute against offline MP4 video clips.
4. **License File**: Verified that no `LICENSE` file currently exists in the root repository. The README accurately documents that all rights are reserved by the project author and reuse permissions should not be assumed.

---

## 7. Confirmation of Code Integrity

* **Zero Source Code Changes**: No backend endpoints, agent logic, database schemas, migration files, mobile Dart classes, or React frontend components were modified.
* **Documentation Scope**: Modifications were strictly confined to creating the root-level [README.md](file:///C:/Programs/codex/SheGuard/README.md) and this [README_VERIFICATION_REPORT.md](file:///C:/Programs/codex/SheGuard/README_VERIFICATION_REPORT.md).
