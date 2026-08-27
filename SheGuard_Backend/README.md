# SheGuard Backend

Standalone FastAPI backend extracted from `SheGuard_AI`.

## Start

```powershell
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Surface

- `POST /register`
- `POST /login`
- `POST /location/update`
- `POST /tracking/start`
- `POST /tracking/update`
- `GET /tracking/live/{session_id}`
- `GET /tracking/history/{session_id}`
- `POST /incident/create`
- `GET /incident/history/{user_id}`
- `GET /incident/live`
- `POST /evidence/upload`
- `GET /evidence/{incident_id}`
- `GET /secure/evidence/{incident_id}`
- `WS /ws/live`
- `WS /ws/tracking/{session_id}`
