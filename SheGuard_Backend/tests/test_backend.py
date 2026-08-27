import json
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app
from app.services.evidence_manager import EvidenceManager
from app.services import telegram_service


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

        token = login.json()["access_token"]
        location = client.post(
            "/location/update",
            json={"user_id": user_id, "latitude": 12.9716, "longitude": 77.5946, "speed": 1.0},
            headers={"Authorization": f"Bearer {token}"},
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
            headers={"Authorization": f"Bearer {token}"},
        )
        assert incident.status_code == 200
        assert incident.json()["incident"]["incident_type"] == "fall"


def test_multipart_incident_uses_per_incident_evidence_folder():
    image = np.full((240, 320, 3), 180, dtype=np.uint8)
    ok, encoded_image = cv2.imencode(".jpg", image)
    assert ok
    real_image_bytes = encoded_image.tobytes()
    video_path = ROOT / "uploads" / "pytest_real_video.mp4"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"mp4v"), 20.0, (320, 240))
    for index in range(30):
        frame = np.full((240, 320, 3), 30 + index, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    real_video_bytes = video_path.read_bytes()
    video_path.unlink(missing_ok=True)

    client = TestClient(app)
    with client:
        # Register and login to get a token
        phone = f"9{str(uuid4().int)[-9:]}"
        register = client.post(
            "/register",
            json={"full_name": "Test User", "phone_number": phone, "password": "secret123"},
        )
        assert register.status_code == 200
        login = client.post("/login", json={"phone_number": phone, "password": "secret123"})
        assert login.status_code == 200
        token = login.json()["access_token"]

        response = client.post(
            "/incidents/create",
            data={
                "incident_type": "fall",
                "confidence": "0.91",
                "latitude": "13.351388",
                "longitude": "77.141865",
                "camera_id": "demo_cctv_1",
                "device_info": "pytest-device",
                "incident_id": "incident_20260513_101500",
                "frame_count": "30",
                "send_alert": "false",
            },
            files={
                "image": ("fall.jpg", real_image_bytes, "image/jpeg"),
                "video": ("fall.mp4", real_video_bytes, "video/mp4"),
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    payload = response.json()
    image_path = Path(payload["image_path"])
    video_path = Path(payload["video_path"])
    incident_dir = image_path.parent
    metadata_path = incident_dir / "metadata.json"

    assert incident_dir.name.startswith("incident_")
    assert incident_dir.parent.name == "incidents"
    assert image_path.name == "frame_1.jpg"
    assert video_path.name == "incident_video.mp4"
    assert image_path.stat().st_size > 1024
    assert video_path.stat().st_size > 4096
    assert image_path.read_bytes() == real_image_bytes
    assert video_path.read_bytes() == real_video_bytes
    assert (incident_dir / "thumbnail.jpg").exists()
    assert (incident_dir / "thumbnail.jpg").read_bytes() == real_image_bytes
    assert metadata_path.exists()
    assert payload["preview_image"].startswith("/uploads/incidents/")
    assert payload["video_url"].endswith("/incident_video.mp4")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["incident_id"].startswith("incident_")
    assert metadata["database_incident_id"] == payload["incident_id"]
    assert metadata["detection_type"] == "fall"
    assert metadata["files"]["frame_1"] == payload["image_path"]
    assert metadata["video_path"] == payload["video_path"]
    assert metadata["frame_count"] == 30
    assert metadata["source_camera"] == "demo_cctv_1"
    assert metadata["device_info"] == "pytest-device"


def test_telegram_alert_sends_text_photo_then_video_with_absolute_paths(tmp_path, monkeypatch):
    image = tmp_path / "frame_1.jpg"
    video = tmp_path / "incident_video.mp4"
    image.write_bytes(b"real-image")
    video.write_bytes(b"real-video")
    calls = []

    class FakeResponse:
        ok = True
        status_code = 200
        text = '"ok": true'

        def json(self):
            return {"ok": True}

    def fake_post(url, **kwargs):
        calls.append((url.rsplit("/", 1)[-1], kwargs))
        files = kwargs.get("files") or {}
        for handle in files.values():
            # handle is a tuple (filename, file_object, content_type)
            file_obj = handle[1] if isinstance(handle, tuple) else handle
            assert Path(file_obj.name).is_absolute()
        return FakeResponse()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setattr(telegram_service.requests, "post", fake_post)
    monkeypatch.setattr(telegram_service.time, "sleep", lambda _: None)
    monkeypatch.setattr(telegram_service, "validate_video_before_telegram", lambda _: None)

    result = telegram_service.send_telegram_alert(
        incident_type="fall",
        confidence=0.95,
        timestamp="10:30 PM",
        image_path=str(image),
        video_path=str(video),
    )

    assert result["message_sent"] is True
    assert result["photo_sent"] is True
    assert result["video_sent"] is True
    assert [call[0] for call in calls[:3]] == ["sendMessage", "sendPhoto", "sendVideo"]


def test_evidence_manager_writes_playable_mp4_with_buffer(tmp_path):
    manager = EvidenceManager(
        evidence_dir=str(tmp_path / "incidents"),
        fps=20.0,
        pre_event_seconds=10.0,
    )
    rng = np.random.default_rng(42)
    pre_frames = [
        rng.integers(0, 255, size=(240, 320, 3), dtype=np.uint8)
        for _ in range(210)
    ]
    post_frames = [
        rng.integers(0, 255, size=(240, 320, 3), dtype=np.uint8)
        for _ in range(210)
    ]
    for frame in pre_frames:
        manager.record_frame(frame)

    result = manager.save_detection_evidence(
        event_frame=pre_frames[-1],
        event_type="fall",
        camera_id="pytest_cam",
        post_event_frames=post_frames,
    )

    image_path = Path(result["image_path"])
    video_path = Path(result["video_path"])
    metadata_path = Path(result["metadata_path"])
    incident_dir = Path(result["incident_dir"])
    assert incident_dir.parent == tmp_path / "incidents"
    assert image_path.parent == incident_dir
    assert video_path.parent == incident_dir
    assert metadata_path.parent == incident_dir
    assert (incident_dir / "frame_1.jpg").exists()
    assert image_path.exists()
    assert video_path.exists()
    assert metadata_path.exists()
    assert video_path.stat().st_size > 100 * 1024

    capture = cv2.VideoCapture(str(video_path))
    try:
        assert capture.isOpened()
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        assert frame_count >= 400
        ok, frame = capture.read()
        assert ok
        assert frame is not None
    finally:
        capture.release()
