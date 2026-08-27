# Import Fix Report

## Backend Import Rewrite

All active backend imports were rewritten from `backend.*` to `app.*`.

Examples:

- `from backend.database import get_db` -> `from app.database import get_db`
- `from backend.models import User` -> `from app.models import User`
- `from backend.services.realtime import realtime_hub` -> `from app.services.realtime import realtime_hub`
- `from backend.app import app` -> `from app.main import app`

## AI Import Decoupling

The AI runtime no longer imports the backend package. Runtime helpers formerly borrowed from `backend.services` were copied into the AI-local `services` package:

- `services/config.py`
- `services/advanced_detectors.py`
- `services/advanced_threat.py`
- `services/cloud_ai.py`
- `services/evidence_manager.py`
- `services/gpu.py`
- `services/stability.py`
- `services/backend_client.py`

`main.py` now imports from `services.*`.

## Scan Result

Active source scan in `SheGuard_AI` for `from backend...`, `import backend...`, and `backend.` returned no matches after excluding virtualenv/generated binary folders.

## Remaining Legacy References

Legacy references exist only under `SheGuard_Backend/migration_sources`, which is retained for audit/recovery and is not used by the active backend or AI runtime.
