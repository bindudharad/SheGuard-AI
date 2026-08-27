from __future__ import annotations

import os
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
import cv2
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger("sheguard.telegram")


@dataclass
class TelegramSendResult:
    enabled: bool
    message_sent: bool = False
    location_sent: bool = False
    photo_sent: bool = False
    video_sent: bool = False
    errors: list[str] = field(default_factory=list)
    responses: dict[str, Any] = field(default_factory=dict)


def telegram_credentials() -> tuple[str | None, str | None]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("PARENT_CHAT_ID") or os.environ.get("CHAT_ID")
    return token, chat_id


def send_telegram_alert(
    *,
    incident_type: str,
    confidence: float,
    timestamp: str,
    latitude: float | None = None,
    longitude: float | None = None,
    image_path: str | None = None,
    video_path: str | None = None,
    live_tracking_url: str | None = None,
    summary: str | None = None,
    chat_id: str | None = None,
) -> dict:
    """Send message, GPS location, emergency image, and emergency video via Telegram."""
    logger.info("telegram_alert_started", extra={
        "incident_type": incident_type,
        "confidence": confidence,
    })
    token, default_chat_id = telegram_credentials()
    target_chat_id = chat_id or default_chat_id
    if not token or not target_chat_id:
        logger.warning("telegram_credentials_missing")
        return TelegramSendResult(
            enabled=False,
            errors=["TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are not configured"],
        ).__dict__

    text = format_emergency_message(
        incident_type=incident_type,
        confidence=confidence,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        live_tracking_url=live_tracking_url,
        summary=summary,
    )

    result = TelegramSendResult(enabled=True)
    base_url = f"https://api.telegram.org/bot{token}"

    # Send text message
    try:
        resp = requests.post(
            f"{base_url}/sendMessage",
            json={"chat_id": target_chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        result.responses["message"] = resp.json()
        if resp.ok:
            result.message_sent = True
            logger.info("telegram_message_sent", extra={"chat_id": target_chat_id})
        else:
            result.errors.append(f"Message: {resp.text}")
            logger.warning("telegram_message_failed", extra={"error": resp.text})
    except Exception as e:
        result.errors.append(f"Message: {e}")
        logger.error("telegram_message_error", extra={"error": str(e)})

    # Send location if coordinates provided
    if latitude is not None and longitude is not None:
        try:
            resp = requests.post(
                f"{base_url}/sendLocation",
                json={"chat_id": target_chat_id, "latitude": latitude, "longitude": longitude},
                timeout=10,
            )
            result.responses["location"] = resp.json()
            if resp.ok:
                result.location_sent = True
                logger.info("telegram_location_sent", extra={"chat_id": target_chat_id})
            else:
                result.errors.append(f"Location: {resp.text}")
                logger.warning("telegram_location_failed", extra={"error": resp.text})
        except Exception as e:
            result.errors.append(f"Location: {e}")
            logger.error("telegram_location_error", extra={"error": str(e)})

    # Send image if provided
    if image_path and Path(image_path).exists():
        try:
            with open(image_path, "rb") as f:
                files = {"photo": (Path(image_path).name, f, "image/jpeg")}
                data = {"chat_id": target_chat_id, "caption": f"📸 Emergency Image - {incident_type}"}
                resp = requests.post(f"{base_url}/sendPhoto", files=files, data=data, timeout=15)
            result.responses["photo"] = resp.json()
            if resp.ok:
                result.photo_sent = True
                logger.info("telegram_photo_sent", extra={"chat_id": target_chat_id, "image_path": image_path})
            else:
                result.errors.append(f"Photo: {resp.text}")
                logger.warning("telegram_photo_failed", extra={"error": resp.text})
        except Exception as e:
            result.errors.append(f"Photo: {e}")
            logger.error("telegram_photo_error", extra={"error": str(e)})

    # Send video if provided
    if video_path and Path(video_path).exists():
        try:
            with open(video_path, "rb") as f:
                files = {"video": (Path(video_path).name, f, "video/mp4")}
                data = {"chat_id": target_chat_id, "caption": f"🎥 Emergency Video - {incident_type}"}
                resp = requests.post(f"{base_url}/sendVideo", files=files, data=data, timeout=30)
            result.responses["video"] = resp.json()
            if resp.ok:
                result.video_sent = True
                logger.info("telegram_video_sent", extra={"chat_id": target_chat_id, "video_path": video_path})
            else:
                result.errors.append(f"Video: {resp.text}")
                logger.warning("telegram_video_failed", extra={"error": resp.text})
        except Exception as e:
            result.errors.append(f"Video: {e}")
            logger.error("telegram_video_error", extra={"error": str(e)})

    logger.info("telegram_alert_complete", extra={
        "message_sent": result.message_sent,
        "location_sent": result.location_sent,
        "photo_sent": result.photo_sent,
        "video_sent": result.video_sent,
        "errors_count": len(result.errors),
    })

    return result.__dict__


def format_emergency_message(
    incident_type: str,
    confidence: float,
    timestamp: str,
    latitude: float | None = None,
    longitude: float | None = None,
    live_tracking_url: str | None = None,
    summary: str | None = None,
) -> str:
    threat_emoji = "🔴" if confidence >= 0.9 else "🟠" if confidence >= 0.75 else "🟡"
    lines = [
        f"{threat_emoji} <b>EMERGENCY ALERT</b> {threat_emoji}",
        f"Type: <b>{incident_type.upper()}</b>",
        f"Confidence: <b>{confidence:.0%}</b>",
        f"Time: <b>{timestamp}</b>",
    ]
    if latitude is not None and longitude is not None:
        lines.append(f"📍 Location: <code>{latitude:.6f}, {longitude:.6f}</code>")
    if live_tracking_url:
        lines.append(f"🔗 Live Tracking: {live_tracking_url}")
    if summary:
        lines.append(f"📝 Summary: {summary}")
    lines.append("\n⚠️ <i>This is an automated emergency alert from SheGuard AI+</i>")
    return "\n".join(lines)


def send_message(token: str, chat_id: str, text: str) -> bool:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.ok
    except Exception:
        return False


def send_location(token: str, chat_id: str, latitude: float, longitude: float) -> bool:
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendLocation",
            json={"chat_id": chat_id, "latitude": latitude, "longitude": longitude},
            timeout=10,
        )
        return resp.ok
    except Exception:
        return False


def send_photo(token: str, chat_id: str, image_path: str, caption: str = "") -> bool:
    try:
        with open(image_path, "rb") as f:
            files = {"photo": (Path(image_path).name, f, "image/jpeg")}
            data = {"chat_id": chat_id, "caption": caption}
            resp = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", files=files, data=data, timeout=15)
        return resp.ok
    except Exception:
        return False


def send_video(token: str, chat_id: str, video_path: str, caption: str = "") -> bool:
    try:
        with open(video_path, "rb") as f:
            files = {"video": (Path(video_path).name, f, "video/mp4")}
            data = {"chat_id": chat_id, "caption": caption}
            resp = requests.post(f"https://api.telegram.org/bot{token}/sendVideo", files=files, data=data, timeout=30)
        return resp.ok
    except Exception:
        return False


def validate_video_before_telegram(video_path: str, max_size_mb: int = 50) -> tuple[bool, str | None]:
    path = Path(video_path)
    if not path.exists():
        return False, "Video file not found"
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"Video too large: {size_mb:.1f} MB (max {max_size_mb} MB)"
    return True, None


def process_incident_alert(
    incident_type: str,
    confidence: float,
    latitude: float | None,
    longitude: float | None,
    image_path: str | None,
    video_path: str | None,
    live_tracking_url: str | None = None,
    summary: str | None = None,
) -> dict:
    """Process and send Telegram alert for an incident."""
    timestamp = datetime.utcnow().isoformat()
    return send_telegram_alert(
        incident_type=incident_type,
        confidence=confidence,
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        image_path=image_path,
        video_path=video_path,
        live_tracking_url=live_tracking_url,
        summary=summary,
    )
