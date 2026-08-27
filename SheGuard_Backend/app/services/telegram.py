import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv


load_dotenv()


def format_alert_text(*, user_name: str, event: str, confidence: float, threat_label: str, latitude: Optional[float], longitude: Optional[float], timestamp: str, summary: str | None) -> str:
    maps_url = "Location unavailable"
    if latitude is not None and longitude is not None:
        maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
    return (
        "SHEGUARD ALERT\n\n"
        f"Possible {event} detected.\n\n"
        f"User: {user_name}\n"
        f"Event: {event}\n"
        f"Confidence: {confidence * 100:.0f}%\n"
        f"Threat Score: {threat_label}\n\n"
        f"Live Location:\n{maps_url}\n\n"
        f"Timestamp:\n{timestamp}\n\n"
        f"AI Summary:\n{summary or 'Local AI detected a dangerous safety event.'}"
    )


def send_telegram_alert(text: str, image_path: str | None = None, video_path: str | None = None) -> dict:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"enabled": False, "message": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured"}

    base = f"https://api.telegram.org/bot{token}"
    message = requests.post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10)
    result = {"enabled": True, "message_sent": message.ok, "photo_sent": False, "video_sent": False}

    if image_path and Path(image_path).exists():
        with open(image_path, "rb") as image_file:
            photo = requests.post(f"{base}/sendPhoto", data={"chat_id": chat_id}, files={"photo": image_file}, timeout=20)
            result["photo_sent"] = photo.ok
    if video_path and Path(video_path).exists():
        with open(video_path, "rb") as video_file:
            video = requests.post(f"{base}/sendVideo", data={"chat_id": chat_id}, files={"video": video_file}, timeout=30)
            result["video_sent"] = video.ok
    return result

