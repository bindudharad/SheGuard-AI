# SheGuard Feature Status / Completeness Matrix

**Generated:** 2026-08-07 · **Mode:** read-only QA verification

Legend: ✅ Verified working · ⚠️ Present but defective/gap · ❌ Missing/blocked · ➖ Not verifiable in this environment

## Backend API coverage

| Area | Endpoints | Status | Notes |
|---|---|---|---|
| Auth | `/register`, `/login`, `/profile/{id}` | ✅ | JWT works with QA secret; 500 with placeholder `.env` secret; authz 403 verified |
| Incidents | `/incidents`, `/incidents/latest`, `/incidents/{id}`, `/incident/history`, `/incident/live`, `/incident/search` | ✅ | Search = in-memory semantic memory (not SQL) |
| Incident create | `/incident/create` (multipart), `/incidents/create` (JSON) | ⚠️ | JSON path works; multipart 500 (python-multipart missing) |
| Evidence | `/evidence/{id}`, `/secure/evidence/{id}`, `/evidence/upload` | ⚠️ | Upload OK (base64); `/evidence/file` unreachable (route shadowed) |
| Tracking | `/tracking/start`, `/tracking/update`, `/tracking/live`, `/tracking/history`, `/track/{id}`, `/track/{id}/qr` | ✅ | REST verified |
| Location | `/location/update`, `/location/live`, `/location/stream` | ✅ | Verified |
| Emergency | `/emergency/start` | ⚠️ | Exists; **`/emergency/status` missing** (Flutter polls it) |
| Contacts | `/contacts/{user_id}`, `/contacts/add` | ✅ | Verified |
| Cameras | `/camera/register`, `/camera/list`, `/camera/health` | ✅ | Verified |
| Notifications | `/notifications/send` | ✅ | Present |
| Realtime | `/ws/live`, `/ws/emergency/{id}`, `/ws/tracking/{id}` | ❌ | 404 — websockets/wsproto not installed |
| System | `/system/local-network`, `/health/gpu`, `/` | ✅ | Root `/` is health; there is **no `/health`** path |

## AI engine

| Capability | Status | Evidence |
|---|---|---|
| YOLOv8 person/pose detection | ✅ | yolov8n.pt loads; video processed |
| MediaPipe pose extraction | ✅ | init OK |
| Legacy RandomForest classifier | ✅ | model.joblib loads; sample pred in 205 ms |
| GRU sequence model v2 | ✅ | checkpoint loads; metrics 0.8538 acc |
| Real-time live detection loop | ✅ | main.py (HybridSafetySystem) runs |
| **Classification accuracy on real videos** | ⚠️ | attack→"fight"; normal→31/33 "fight" (false positives) |
| CUDA inference | ❌ | CPU-only build |

## Dashboard

| Capability | Status | Notes |
|---|---|---|
| Build | ✅ | `npm run build` OK (~10 s) |
| Login | ✅ | Works against localhost:8000 |
| Incidents list / latest | ✅ | 200 verified |
| Live map (react-leaflet + OSM) | ✅ | Needs internet |
| WebSocket live feed | ➖ | Not implemented in dashboard (polling only) |
| Incident title/address mapping | ⚠️ | `normalizeIncident` uses `raw.type` (backend sends `incident_type`) → always "SOS Emergency" |
| API base URL config | ⚠️ | Hardcoded default `http://192.168.1.3:8000` in `src/config.js:1`; needs `VITE_API_BASE_URL` at **build** time |

## Flutter app

| Capability | Status | Notes |
|---|---|---|
| `flutter analyze` | ✅ | No issues |
| `flutter test` | ✅ | 6/6 pass |
| `flutter pub get` | ✅ | 81 newer versions available |
| APK build | ❌ | Blocked: broken JAVA_HOME, no jlink.exe in available JBR |
| Runtime on device/emulator | ➖ | No AVDs/devices |
| SOS / auto-SOS / countdown | ✅ (code) | Calls `/incidents/create` + `/emergency/start` |
| **Emergency status polling** | ❌ | `/emergency/status` endpoint missing on backend |
| Realtime WS | ❌ | `/ws/live` 404 at runtime |
| Evidence capture + encrypt | ✅ (code) | `AES` via `cryptography`, base64 upload matches schema |
| Hardcoded IP | ⚠️ | `lib/config/api_config.dart:2` → `192.168.1.3:8000` |
| Background location/tracking | ✅ (code) | `flutter_background_service` + foreground service |

## Cross-cutting

| Concern | Status |
|---|---|
| REST↔Flutter payload schemas | ✅ match (incident JSON, evidence upload) |
| REST↔Dashboard payload schemas | ⚠️ title/address field mismatch |
| WebSocket (any client) | ❌ broken |
| Telegram / Groq / Gemini cloud alerts | ⚠️ configured in `.env`; live calls only on alert path (Telegram timeout seen in old logs) |

## Feature completeness score

- Backend REST: **~90%** complete (2 blockers: multipart, `/emergency/status`)
- Realtime layer: **0%** operational (WS dead)
- AI engine: **~85%** (runs, but accuracy on real footage is poor)
- Dashboard: **~80%** (2 data-mapping/config issues)
- Flutter: **~75%** (build blocked, 1 missing endpoint, hardcoded IP)

**Overall feature completeness: 7 / 10**

