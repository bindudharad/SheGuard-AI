# Final Architecture

## Backend

```text
SheGuard_Backend/
├── app/
│   ├── api/
│   ├── routes/
│   ├── database/
│   ├── models/
│   ├── services/
│   ├── websocket/
│   ├── auth/
│   ├── core/
│   ├── middleware/
│   └── main.py
├── uploads/
├── logs/
├── tests/
├── requirements/
├── requirements-api.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .env
├── sheguard.db
└── README.md
```

## AI

```text
SheGuard_AI/
├── main.py
├── services/
│   ├── backend_client.py
│   ├── config.py
│   ├── evidence_manager.py
│   ├── cloud_ai.py
│   ├── gpu.py
│   ├── stability.py
│   ├── advanced_detectors.py
│   └── advanced_threat.py
├── utils/
├── models/
├── dataset/
├── raw_videos/
├── evidence/
├── captures/
├── clips/
├── train.py
├── train_v2.py
├── predict.py
├── requirements-ai.txt
└── requirements-dev.txt
```

## Startup

Backend:

```powershell
cd C:\Programs\codex\SheGuard\SheGuard_Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

AI:

```powershell
cd C:\Programs\codex\SheGuard\SheGuard_AI
python main.py --backend-url http://localhost:8000
```

## Dependency Map

```text
Flutter/Dashboard
-> SheGuard_Backend app.routes
-> app.database/app.models
-> app.services.realtime
-> SQLite + websocket clients

SheGuard_AI main.py
-> utils.detection / utils.tracking
-> ActionClassifier / ActionSequenceClassifier
-> services.evidence_manager
-> services.cloud_ai
-> services.backend_client
-> HTTP API only
```
