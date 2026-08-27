from fastapi.testclient import TestClient
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import app


def test_backend_core_flow():
    phone = f"9{str(uuid4().int)[-9:]}"
    client = TestClient(app)
    with client:
        register = client.post(
            "/register",
            json={"full_name": "Test User", "phone_number": phone, "password": "secret123"},
        )
        assert register.status_code == 200

        login = client.post("/login", json={"phone_number": phone, "password": "secret123"})
        assert login.status_code == 200
        user_id = login.json()["user_id"]

        location = client.post(
            "/location/update",
            json={"user_id": user_id, "latitude": 12.9716, "longitude": 77.5946, "speed": 1.0},
        )
        assert location.status_code == 200

        incident = client.post(
            "/incident/create",
            json={
                "user_id": user_id,
                "incident_type": "fall",
                "confidence": 0.9,
                "ai_summary": "Test incident",
                "send_alert": False,
            },
        )
        assert incident.status_code == 200
        assert incident.json()["incident"]["incident_type"] == "fall"
