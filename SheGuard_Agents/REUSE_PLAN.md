# SheGuard Reuse Plan

**Date**: 2026-08-18
**Purpose**: Precise decisions on what to REUSE (wrap), ADAPT (refactor), or REWRITE for `SheGuard_agents`. This supersedes the earlier draft `REUSE_PLAN.md` with corrections found during the audit (notably: live secrets must not be reused; the existing `core/*.py` had corrupted Python now fixed; legacy risk is 0–10 not 0–100).

---

## 0. Hard Rules
1. **Do NOT modify** `SheGuard_AI`, `SheGuard_Backend`, `SheGuard_App`, `SheGuard_Dashboard` (unless explicitly requested).
2. **Do NOT copy the backend `.env`** (contains live secrets). Use `.env.example` placeholders only. Rotate those tokens upstream.
3. **Do NOT make the Flutter APK a dependency**.
4. **Do NOT claim** an agent works / payment is real / model accuracy measured unless verified with tests.

---

## 1. Direct Reuse (wrap as-is or minimal adapter)

| Component | Source | Target | Effort |
|-----------|--------|--------|--------|
| YOLOv8n detection | `SheGuard_AI/utils/detection.py::detect_people()` | `agents/vision/detector.py` | Low |
| MediaPipe pose | `SheGuard_AI/utils/detection.py::estimate_pose()` | `agents/vision/pose.py` | Low |
| SimpleTracker | `SheGuard_AI/utils/tracking.py` | `agents/vision/tracker.py` | Low |
| GRU temporal classifier | `SheGuard_AI/action_sequence_classifier.py` + `models/v2/*` | `agents/vision/temporal.py` | Low (valid 85% acc) |
| EventClipBuffer | `SheGuard_AI/video_clipper.py` | `agents/response/evidence.py` (add SHA-256 + retention) | Low |
| Backend evidence manager | `SheGuard_Backend/app/services/evidence_manager.py` + `media_storage.py` | `services/evidence/` | Low |
| Telegram sender logic | `SheGuard_Backend/app/services/telegram_service.py` | `agents/response/notification.py` (remove prints, add `TEST_MODE`) | Low |
| Risk scoring pattern | `SheGuard_Backend/app/services/advanced_threat.py` | `core/risk_engine.py` (rescale 0–10 → 0–100, YAML weights) | Low |
| BaseAgent/AgentStatus/AgentMessage/EventBus/Registry | `SheGuard_agents/core/agent.py`, `core/event_bus.py` (**repaired this audit**) | `core/` (split into agent_state/message/registry) | Low |
| SQLAlchemy 2.0 models pattern | `SheGuard_Backend/app/models/entities.py` | new SQLAlchemy models for agent DB | Low |

---

## 2. Adapt & Refactor

| Existing | Adaptation |
|----------|------------|
| `HybridSafetySystem.run()` | Convert to event-driven Vision Agent (`process(message)` loop) emitting `FRAME_PROCESSED` events |
| `LocalSafetyAnalyzer` rules | Wrap as Vision Agent rule-based fallback with **neutral** labels (possible_confrontation, possible_physical_aggression) |
| `advanced_threat.assess_threat()` | Transparent weighted formula, configurable weights via `config/thresholds.yaml`, 0–100 scale, reasons array |
| `GroqVisionClient` | Refactor as SafetyIntelligenceService backend (x402 target); improve structured output beyond keyword heuristic |
| `CloudAIOrchestrator` | Reference for multi-provider x402 orchestration |
| `RealtimeHub` | Replace with `core/event_bus.py`; add `/ws/events` + SSE for dashboard |
| `incidents`/`evidence` DB schema | New clean agent schema (`agent_incidents`, `agent_evidence`, `x402_payments`, `agents`, `agent_events`) |
| `/incidents` API shapes | Keep near-compatible so legacy dashboard/app can later consume new API |

---

## 3. Rewrite / New Implementation

### 3.1 Core infrastructure (all new)
- `core/exceptions.py` — `AgentError`, `AgentUnavailable`, `ConfidenceTooLow`, `PaymentError`
- `core/agent_state.py` — `AgentStatus`, `AgentHealth` (split from current `agent.py`)
- `core/message.py` — `AgentMessage`, `Event` schema (split from current `event_bus.py`)
- `core/agent.py` — `BaseAgent` (repaired; align with new state/message modules)
- `core/agent_registry.py` — standalone registry (currently inside `event_bus.py`)
- `core/event_bus.py` — pub/sub (repaired; use `message.py` types)
- `core/pipeline.py` — agent pipeline composition helpers
- `core/confidence.py` — confidence aggregation/calibration
- `core/risk_engine.py` — transparent weighted 0–100 scoring + explainability
- `core/orchestrator.py` — lifecycle, dispatch, incident state, retries, dedup, graceful failure

### 3.2 Agents (all new)
- `agents/vision/` — orchestrates detector + pose + tracker + temporal (wrap existing)
- `agents/audio/` — adapter interface + deterministic/mock detector (no real speech recognition claimed)
- `agents/context/` — time/location/zone/history providers (no bias from person attributes)
- `agents/threat/` — combines vision+audio+context, risk + explainability
- `agents/decision/` — uncertainty reasoning + safety policy (NOT `if risk>80: emergency()`)
- `agents/x402/` — payment orchestration, Algorand wallet, payment state machine, service client
- `agents/response/` — incident lifecycle, evidence, notification, location

### 3.3 x402 / Algorand (all new)
- `services/safety_intelligence/` — HTTP 402 endpoint + analyzer
- `agents/x402/` — Algorand testnet payment (simulation mode first)
- Payment audit trail (`x402_payments` table)

### 3.4 API / Simulation / Tests (all new)
- `api/` — FastAPI: `/health`, `/agents`, `/incidents`, `/analysis/frame|video`, `/simulation/incident`, `/events` (SSE), `/ws/events`, `/x402/*`, `/payments`
- `simulation/` — NORMAL/SUSPICIOUS/HIGH_RISK/CRITICAL/X402_UNCERTAIN/EMERGENCY scenarios
- `scripts/` — `start.py`, `health_check.py`, `run_demo.py`, `run_all_tests.py`
- `tests/` — unit / integration / agents / api / x402 / end_to_end

---

## 4. What NOT to Reuse (explicitly excluded)

| Component | Reason |
|-----------|--------|
| `SheGuard_AI/main.py` | Monolithic sync loop; replace with agent pipeline |
| `SheGuard_Backend/app/routes/incidents.py` | Complex duplicate/merge logic; new API is independent |
| `SheGuard_Backend/app/services/threat.py` | Thin wrapper; replaced by configurable RiskEngine |
| `SheGuard_Backend/app/services/advanced_threat.py` | 0–10 scale, partial config; adapt pattern only |
| `SheGuard_AI/utils/detection.py::LocalSafetyAnalyzer` | Split into detector/pose/temporal/rule modules |
| `SheGuard_Backend/app/services/incident_memory.py` | Replace with Context Agent historical provider (or reuse logic only) |
| `SheGuard_Backend/app/services/realtime.py` | Replace with `core/event_bus.py` |
| `SheGuard_Backend/.env` | **Contains live secrets** — NEVER reuse |
| `advanced_detectors.py` | Stubs returning no real signal |

---

## 5. Configuration Migration

| Old Var | New Var | Notes |
|---------|---------|-------|
| `GROQ_API_KEY` | `GROQ_API_KEY` | same |
| `GROQ_VISION_MODEL` | `GROQ_VISION_MODEL` | same |
| `TELEGRAM_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` | same (never committed) |
| `TELEGRAM_CHAT_ID` | `TELEGRAM_CHAT_ID` | same |
| `SHEGUARD_DB_PATH` | `AGENTS_DB_PATH` | new separate DB |
| `SHEGUARD_JWT_SECRET` | `AGENTS_JWT_SECRET` | new secret |
| — | `X402_MODE` | `simulation|testnet` |
| — | `X402_SERVICE_URL` | safety-intelligence endpoint |
| — | `ALGORAND_NETWORK` | `testnet|mainnet` |
| — | `ALGORAND_RPC_URL` | Algorand node |
| — | `ALGORAND_WALLET_ADDRESS` | payment wallet |
| — | `ALGORAND_PRIVATE_KEY` | **never commit, never log** |
| — | `AI_MODE` | `existing|simulation` |
| — | `TEST_MODE` | `true` → simulated notifications |

---

## 6. File Copy Checklist (for implementation)

### Copy (then refactor)
- [ ] `SheGuard_AI/yolov8n.pt` → `SheGuard_agents/models/`
- [ ] `SheGuard_AI/models/v2/*` (GRU) → `SheGuard_agents/models/v2/`
- [ ] `SheGuard_AI/utils/tracking.py` → `agents/vision/tracker.py`
- [ ] `SheGuard_AI/video_clipper.py` → `agents/response/evidence.py`
- [ ] `SheGuard_AI/groq_client.py` → `services/safety_intelligence/groq_client.py`
- [ ] `SheGuard_Backend/app/services/telegram_service.py` → `agents/response/notification.py` (strip prints)

### Reference only (do not copy)
- [ ] `SheGuard_AI/utils/detection.py`, `feature_extractor.py`, `sequence_features.py`
- [ ] `SheGuard_AI/action_classifier.py`, `action_sequence_classifier.py`
- [ ] `SheGuard_Backend/app/services/advanced_threat.py`, `cloud_ai.py`, `evidence_manager.py`, `media_storage.py`, `realtime.py`
- [ ] `SheGuard_Backend/app/models/entities.py`, `app/api/schemas.py`
- [ ] `SheGuard_Dashboard/src/services/api.js`

### Do NOT touch
- [ ] `SheGuard_Backend/.env` (live secrets)
- [ ] Any legacy APK
- [ ] Legacy `sheguard.db` (read-only)
