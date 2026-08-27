# API Decoupling Report

## Direct Couplings Removed

`SheGuard_AI/main.py` previously imported backend config, GPU, threat, evidence, cloud AI, stability, and detector helper modules. These imports have been replaced with AI-local services.

The direct `requests.post()` incident call was replaced by `services.backend_client.BackendClient`.

## Backend Client

Created `C:\Programs\codex\SheGuard\SheGuard_AI\services\backend_client.py` with:

- `create_incident()`
- `upload_evidence()`
- `send_tracking_update()`
- `create_alert()`
- async incident/tracking helpers
- websocket URL helpers for `/ws/live` and `/ws/tracking/{session_id}`

Default backend base URL is `http://localhost:8000`. The client also accepts the legacy endpoint form `http://localhost:8000/incident/create` and normalizes it to the base URL.

## API Contracts Preserved

- `POST /incident/create`
- `POST /evidence/upload`
- `POST /tracking/start`
- `POST /tracking/update`
- `GET /tracking/live/{session_id}`
- `GET /tracking/history/{session_id}`
- `WS /ws/live`
- `WS /ws/tracking/{session_id}`

## Runtime Flow

AI detection now flows as:

```text
YOLO/MediaPipe/classifiers
-> local evidence files in SheGuard_AI/evidence
-> BackendClient.create_incident()
-> SheGuard_Backend FastAPI API
-> SQLAlchemy/SQLite + websocket publish + optional Telegram alert
```

## Remaining Risks

- Evidence paths sent to the backend are local filesystem paths from the AI process. If AI and backend run on different machines/containers, use `upload_evidence()` or shared storage.
- `BackendClient` logs failures and lets the AI runtime continue, so offline backend behavior is fail-soft by design.
