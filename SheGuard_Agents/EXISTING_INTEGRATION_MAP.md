# SheGuard Existing Integration Map

**Date**: 2026-08-18
**Purpose**: Document all external and internal integrations for reuse planning. The new `SheGuard_agents` will replicate/extend some, and introduce new ones (x402/Algorand).

---

## 1. External Service Integrations (Legacy)

| Service | Purpose | Config | Client | Reuse for SheGuard_agents |
|---------|---------|--------|--------|---------------------------|
| **Telegram Bot API** | Emergency alerts (msg/photo/video/location) | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`/`PARENT_CHAT_ID` | `SheGuard_Backend/app/services/telegram_service.py::send_telegram_alert` | **WRAP** in ResponseAgent.notification — remove debug `print()` noise, add `TEST_MODE` guard. |
| **Groq Vision** | Cloud AI verification of local events | `GROQ_API_KEY`, `GROQ_VISION_MODEL` | `SheGuard_AI/groq_client.py::GroqVisionClient` | **PATTERN** for Safety Intelligence Service (x402 target). Current danger=keyword heuristic; needs better structured output. |
| **Gemini API** | Fallback cloud AI | `GEMINI_API_KEY` | `SheGuard_Backend/app/services/cloud_ai.py::CloudAIOrchestrator._try_gemini` | Alternative x402 provider. |
| **OpenRouter API** | Fallback cloud AI | `OPENROUTER_API_KEY` | `SheGuard_Backend/app/services/cloud_ai.py::CloudAIOrchestrator._try_openrouter` | Alternative x402 provider. |
| **NVIDIA / HF Embeddings** | Text embeddings for incident memory | `NVIDIA_API_KEY` or `HF_API_KEY` | `SheGuard_Backend/app/services/cloud_ai.py::EmbeddingClient` | Context Agent historical similarity (deterministic fallback acceptable for MVP). |

---

## 2. Internal Component Integrations (Current Pipeline)

```
SheGuard_AI (CV loop)
    │
    ├─▶ POST /incidents/create ──▶ SheGuard_Backend (FastAPI)
    │                                 │
    │                                 ├─▶ SQLite (incidents, evidence, users, sessions)
    │                                 ├─▶ Telegram (message → photo → video → location)
    │                                 ├─▶ Cloud AI (Groq → Gemini → OpenRouter → local)
    │                                 ├─▶ RealtimeHub (in-memory WS broadcast)
    │                                 │
    │                                 ├─▶ Dashboard (polling /incidents, /incidents/latest @ 2s)
    │                                 └─▶ Mobile App (WS /ws/live + same REST)
```

### 2.1 SheGuard_AI → Backend
- **Protocol**: HTTP POST JSON or multipart to `/incidents/create` or `/incidents/create`
- **Auth**: `SHEGUARD_SERVICE_TOKEN` (Bearer)
- **Payload**: `IncidentCreate` schema (type, confidence, lat/lon, image/video paths, camera_id, explanation, send_alert)
- **Error handling**: Logs and continues local processing.

### 2.2 Backend → Telegram
- **Trigger**: After incident finalized + media stored
- **Flow**: `incident_session._send_session_telegram` → `telegram_service.send_telegram_alert`
- **Sequence**: sendMessage → sendPhoto → sendVideo (validated >100KB, re-readable) → sendLocation
- **Timeouts**: 15s (msg), 120s (video)

### 2.3 Backend → Dashboard / App
- **Dashboard**: Polling `GET /incidents`, `GET /incidents/latest` every 2s. `normalizeIncident()` tolerates field aliases (0–1/0–100 confidence, lat/lng/address variants).
- **App**: WS `ws://base/ws/live?user_id=&token=` + REST. Expects `incident.created` / `incident.merged` envelopes with `payload.incident` (full incident + media URLs).

### 2.4 Evidence Storage
- **Local FS**: `uploads/incidents/incident_<timestamp>/` — frame.jpg, incident_video.mp4, thumbnail.jpg, metadata.json
- **Validation**: size > 50KB, re-readable via `cv2.VideoCapture`
- **Config**: `config.yaml` `evidence.pre_event_seconds` (30), `post_event_seconds` (30), `retention_days` (30)

### 2.5 Incident Memory (Semantic Search)
- **Backend**: `SheGuard_Backend/app/services/incident_memory.py::IncidentMemory`
- **Embeddings**: `EmbeddingClient` (Gemini/HF/NVIDIA) or deterministic hash fallback
- **API**: `GET /incident/search?q=...` → similarity matches
- **Reuse**: Context Agent historical context provider.

---

## 3. Video Input Sources (SheGuard_AI)
| Source | Integration | Config |
|--------|-------------|--------|
| DroidCam | OpenCV `VideoCapture` indices 1,2 | Auto-reconnect (configurable delay/attempts) |
| RTSP/IP Camera | OpenCV `VideoCapture` URL | `camera_config.json` (`droidcam_source`) |
| Video File | OpenCV `VideoCapture` path | `--source` arg |
| USB Camera | OpenCV `VideoCapture` index 0 | `--source 0` |

---

## 4. Shared Configuration (Env Variables)
| Variable | Used By | Purpose |
|----------|---------|---------|
| `SHEGUARD_DB_PATH` | AI, Backend | SQLite file |
| `SHEGUARD_JWT_SECRET` | AI, Backend | JWT signing |
| `GROQ_API_KEY` | AI, Backend | Groq Vision |
| `GROQ_VISION_MODEL` | AI, Backend | Model name |
| `TELEGRAM_BOT_TOKEN` | AI, Backend | Telegram bot |
| `TELEGRAM_CHAT_ID` | AI, Backend | Telegram chat |
| `PARENT_CHAT_ID` | Backend | Alt chat ID |
| `SHEGUARD_SERVICE_TOKEN` | Backend | Service auth (AI→Backend) |
| `SHEGUARD_CORS_ORIGINS` | Backend | CORS |

> **SECURITY**: `.env` in Backend contains **live secrets** — never copy to `SheGuard_agents`. Use `.env.example` only.

---

## 5. Integration Patterns for SheGuard_agents (NEW)

### 5.1 Agent-to-Agent (Internal)
- **Mechanism**: `core/event_bus.py` — asyncio pub/sub with `AgentMessage` (trace_id, incident_id, confidence, data).
- **No direct calls**: Agents communicate only via events.

### 5.2 Agent-to-External (Outbound)
- **HTTP clients**: `httpx`/`requests` with retry/timeout/circuit-breaker.
- **Auth**: API keys from `config/settings.py` (Pydantic Settings).

### 5.3 External-to-Agent (Inbound)
- **FastAPI**: Endpoints with JWT or service-token auth.
- **Rate limiting**: Per-agent quotas (future).

### 5.4 Agent-to-Persistence
- **Direct SQLite** (SQLAlchemy 2.0) for low latency — own DB `sheguard_agents.db`.

---

## 6. Compatibility Matrix

| Integration | Legacy State | SheGuard_agents Approach |
|-------------|--------------|--------------------------|
| YOLOv8n | Working | VisionAgent.detector (direct wrap) |
| MediaPipe Pose | Working | VisionAgent.pose (direct wrap) |
| GRU Temporal | Conditional (85% acc) | VisionAgent.temporal (wrap, DEMO if missing) |
| Groq API | Working | SafetyIntelligenceService (x402 target) |
| Telegram | Working | ResponseAgent.notification (cleaned) |
| SQLite | Working | New agent DB + read legacy if needed |
| FastAPI Backend | Working | New independent API (reference only) |
| WebSocket | Working (in-memory) | New Event Bus + `/ws/events` |
| Dashboard | Polling | Consumes new APIs (Phase 9) |
| Mobile App | Broken WS | Phase 2/3 (not blocker) |
| x402 / Algorand | **Missing** | **New implementation** (Phase 6–7) |
