import tempfile
from pathlib import Path
import sys
sys.path.insert(0, ".")
from app.services import telegram_service
import requests

# Create temp files
with tempfile.TemporaryDirectory() as tmp_path:
    image = Path(tmp_path) / "frame_1.jpg"
    video = Path(tmp_path) / "incident_video.mp4"
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
            print("handle.name:", handle.name)
            print("is_absolute:", Path(handle.name).is_absolute())
        return FakeResponse()
    
    # Monkey patch
    import app.services.telegram_service as ts
    original_post = ts.requests.post
    ts.requests.post = fake_post
    original_sleep = ts.time.sleep
    ts.time.sleep = lambda _: None
    original_validate = ts.validate_video_before_telegram
    ts.validate_video_before_telegram = lambda _: None
    
    try:
        result = ts.send_telegram_alert(
            incident_type="fall",
            confidence=0.95,
            timestamp="10:30 PM",
            image_path=str(image),
            video_path=str(video),
        )
        print("result:", result)
        print("calls:", calls)
    finally:
        ts.requests.post = original_post
        ts.time.sleep = original_sleep
        ts.validate_video_before_telegram = original_validate
