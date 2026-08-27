from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
INCIDENT_ROOT = UPLOAD_ROOT / "incidents"
MIN_REAL_IMAGE_BYTES = 1024
MIN_REAL_VIDEO_BYTES = 4096
logger = logging.getLogger("sheguard.media_storage")


@dataclass(frozen=True)
class StoredIncidentMedia:
    image_path: str | None = None
    video_path: str | None = None
    thumbnail_path: str | None = None
    metadata_path: str | None = None
    incident_dir: str | None = None
    frame_paths: list[str] = field(default_factory=list)
    frame_count: int | None = None
    image_error: str | None = None
    video_error: str | None = None


def store_incident_media(
    *,
    image_path: str | None,
    video_path: str | None,
    incident_time: datetime,
    incident_folder_id: str | None = None,
    incident_type: str | None = None,
    confidence: float | None = None,
    frame_count: int | None = None,
    metadata_path: str | None = None,
) -> StoredIncidentMedia:
    """Copy locally reachable AI evidence into one backend incident folder."""
    existing = _existing_backend_incident_media(
        image_path=image_path,
        video_path=video_path,
        metadata_path=metadata_path,
        frame_count=frame_count,
    )
    if existing:
        return existing

    incident_dir = create_incident_folder(incident_time, incident_folder_id)
    image_target = incident_dir / "frame_1.jpg"
    thumbnail_target = incident_dir / "thumbnail.jpg"
    video_target = incident_dir / "incident_video.mp4"

    stored_image, image_error = _copy_media(image_path, image_target, media_type="image")
    stored_thumbnail = None
    if stored_image:
        shutil.copy2(stored_image, thumbnail_target)
        stored_thumbnail = thumbnail_target
    stored_video, video_error = _copy_media(video_path, video_target, media_type="video")
    metadata_path = incident_dir / "metadata.json"
    _write_initial_metadata(
        metadata_path=metadata_path,
        incident_folder_id=incident_dir.name,
        incident_type=incident_type,
        confidence=confidence,
        timestamp=incident_time,
        frame_count=frame_count,
        image_path=stored_image,
        thumbnail_path=stored_thumbnail,
        video_path=stored_video,
    )
    return StoredIncidentMedia(
        image_path=str(stored_image) if stored_image else None,
        video_path=str(stored_video) if stored_video else None,
        thumbnail_path=str(stored_thumbnail) if stored_thumbnail else None,
        metadata_path=str(metadata_path),
        incident_dir=str(incident_dir),
        frame_paths=[str(stored_image)] if stored_image else [],
        frame_count=frame_count,
        image_error=image_error,
        video_error=video_error,
    )


async def store_uploaded_incident_media(
    *,
    image_file: Any | None,
    video_file: Any | None,
    incident_time: datetime,
    incident_folder_id: str | None = None,
    incident_dir: str | Path | None = None,
    thumbnail_file: Any | None = None,
    metadata_file: Any | None = None,
    incident_type: str | None = None,
    confidence: float | None = None,
    frame_count: int | None = None,
) -> StoredIncidentMedia:
    """Persist actual multipart CCTV evidence under uploads/incidents/<incident_id>/."""
    folder = Path(incident_dir) if incident_dir else create_incident_folder(incident_time, incident_folder_id)
    folder.mkdir(parents=True, exist_ok=True)
    image_target = _next_numbered_path(folder, "frame", ".jpg")
    video_target = folder / "incident_video.mp4" if not (folder / "incident_video.mp4").exists() else _next_numbered_path(folder, "clip", ".mp4")

    image_path, image_error = await _save_upload(image_file, image_target, media_type="image")
    thumbnail_path, thumbnail_error = await _save_upload(thumbnail_file, folder / "thumbnail.jpg", media_type="image")
    if not thumbnail_path and image_path and not (folder / "thumbnail.jpg").exists():
        try:
            shutil.copy2(image_path, folder / "thumbnail.jpg")
            thumbnail_path = folder / "thumbnail.jpg"
        except OSError as exc:
            thumbnail_error = str(exc)
    elif (folder / "thumbnail.jpg").exists():
        thumbnail_path = folder / "thumbnail.jpg"
    video_path, video_error = await _save_upload(video_file, video_target, media_type="video")

    metadata_path = folder / "metadata.json"
    uploaded_metadata = await _read_json_upload(metadata_file)
    _write_initial_metadata(
        metadata_path=metadata_path,
        incident_folder_id=folder.name,
        incident_type=incident_type,
        confidence=confidence,
        timestamp=incident_time,
        frame_count=frame_count,
        image_path=image_path,
        thumbnail_path=thumbnail_path,
        video_path=video_path,
        uploaded_metadata=uploaded_metadata,
    )

    if image_path:
        _print_received("[BACKEND] image received", image_path)
    if thumbnail_path:
        _print_received("[BACKEND] thumbnail received", thumbnail_path)
    if video_path:
        _print_received("[BACKEND] video received", video_path)
        print("video saved:", video_path)

    return StoredIncidentMedia(
        image_path=str(image_path) if image_path else None,
        video_path=str(video_path) if video_path else None,
        thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
        metadata_path=str(metadata_path),
        incident_dir=str(folder),
        frame_paths=[str(image_path)] if image_path else [],
        frame_count=frame_count,
        image_error=image_error or thumbnail_error,
        video_error=video_error,
    )


def create_incident_folder(incident_time: datetime, incident_folder_id: str | None = None, root: Path | str | None = None) -> Path:
    root_path = Path(root) if root else INCIDENT_ROOT
    root_path.mkdir(parents=True, exist_ok=True)
    base_name = _safe_incident_id(incident_folder_id) if incident_folder_id else incident_time.strftime("incident_%Y%m%d_%H%M%S")
    base = root_path / base_name
    if not base.exists():
        base.mkdir(parents=True)
        return base
    for index in range(1, 1000):
        candidate = root_path / f"{base_name}_{index}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
    candidate = root_path / f"{base_name}_{int(datetime.utcnow().timestamp())}"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def write_incident_metadata(
    *,
    metadata_path: str | None,
    incident_id: int,
    timestamp: datetime,
    incident_type: str,
    confidence: float,
    latitude: float | None,
    longitude: float | None,
    source_camera: str | None,
    device_info: str | None,
    telegram_status: dict | None,
    image_path: str | None,
    video_path: str | None,
    frame_paths: list[str] | None = None,
    frame_count: int | None = None,
) -> str | None:
    """Write final metadata.json inside the same incident evidence folder."""
    if not metadata_path:
        return None
    incident_folder_id = Path(metadata_path).parent.name
    payload = {
        "incident_id": incident_folder_id,
        "database_incident_id": incident_id,
        "detection_type": incident_type,
        "confidence": confidence,
        "timestamp": timestamp.isoformat(),
        "frame_count": int(frame_count or 0),
        "video_path": video_path,
        "image_path": image_path,
        "gps": {"latitude": latitude, "longitude": longitude},
        "source_camera": source_camera,
        "device_info": device_info,
        "telegram_message_status": {
            "enabled": bool((telegram_status or {}).get("enabled")),
            "message_sent": bool((telegram_status or {}).get("message_sent")),
            "location_sent": bool((telegram_status or {}).get("location_sent")),
            "photo_sent": bool((telegram_status or {}).get("photo_sent")),
            "video_sent": bool((telegram_status or {}).get("video_sent")),
            "errors": (telegram_status or {}).get("errors") or [],
        },
        "files": {
            "frame_1": image_path,
            "thumbnail": str(Path(image_path).with_name("thumbnail.jpg")) if image_path else None,
            "incident_video": video_path,
            "frames": frame_paths or [],
        },
    }
    _write_json(Path(metadata_path), payload)
    return metadata_path


async def _save_upload(upload: Any | None, target: Path, *, media_type: str) -> tuple[Path | None, str | None]:
    if not upload or not getattr(upload, "filename", None):
        return None, f"missing_{media_type}_upload"
    try:
        data = await upload.read()
        error = _validate_media_bytes(data, media_type=media_type, filename=str(upload.filename))
        if error:
            return None, error
        target.write_bytes(data)
        return target, None
    except Exception as exc:
        return None, str(exc)


def _copy_media(source: str | None, target: Path, *, media_type: str) -> tuple[Path | None, str | None]:
    if not source:
        return None, f"missing_{media_type}_path"
    source_path = Path(source)
    if not source_path.exists() or not source_path.is_file():
        return None, f"{media_type}_not_found:{source}"
    data = source_path.read_bytes()
    error = _validate_media_bytes(data, media_type=media_type, filename=source_path.name)
    if error:
        return None, error
    shutil.copy2(source_path, target)
    return target, None


def _validate_media_bytes(data: bytes, *, media_type: str, filename: str) -> str | None:
    if media_type == "image":
        if len(data) < MIN_REAL_IMAGE_BYTES:
            return f"image_too_small_or_empty:{filename}"
        if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG")):
            return f"image_not_jpeg_or_png:{filename}"
    if media_type == "video":
        if len(data) < MIN_REAL_VIDEO_BYTES:
            return f"video_too_small_or_empty:{filename}"
        if b"ftyp" not in data[:64]:
            return f"video_not_mp4:{filename}"
    return None


def _existing_backend_incident_media(
    *,
    image_path: str | None,
    video_path: str | None,
    metadata_path: str | None,
    frame_count: int | None,
) -> StoredIncidentMedia | None:
    image = Path(image_path).resolve() if image_path else None
    video = Path(video_path).resolve() if video_path else None
    if not image or not video:
        return None
    try:
        incident_root = INCIDENT_ROOT.resolve()
        image.relative_to(incident_root)
        video.relative_to(incident_root)
    except (OSError, ValueError):
        return None
    if not image.exists() or not video.exists():
        return None
    image_error = _validate_media_bytes(image.read_bytes(), media_type="image", filename=image.name)
    video_error = _validate_media_bytes(video.read_bytes(), media_type="video", filename=video.name)
    if image_error or video_error:
        return StoredIncidentMedia(
            image_path=str(image) if not image_error else None,
            video_path=str(video) if not video_error else None,
            metadata_path=metadata_path,
            incident_dir=str(image.parent),
            frame_paths=[str(image)] if not image_error else [],
            frame_count=frame_count,
            image_error=image_error,
            video_error=video_error,
        )
    metadata = Path(metadata_path).resolve() if metadata_path else image.parent / "metadata.json"
    thumbnail = image.parent / "thumbnail.jpg"
    if not thumbnail.exists():
        try:
            shutil.copy2(image, thumbnail)
        except OSError:
            thumbnail = None
    return StoredIncidentMedia(
        image_path=str(image),
        video_path=str(video),
        thumbnail_path=str(thumbnail) if thumbnail and thumbnail.exists() else None,
        metadata_path=str(metadata),
        incident_dir=str(image.parent),
        frame_paths=[str(image)],
        frame_count=frame_count,
    )


async def _read_json_upload(upload: Any | None) -> dict | None:
    if not upload or not getattr(upload, "filename", None):
        return None
    try:
        data = await upload.read()
        if not data:
            return None
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        print("ERROR:", exc)
        return None


def _write_initial_metadata(
    *,
    metadata_path: Path,
    incident_folder_id: str,
    incident_type: str | None,
    confidence: float | None,
    timestamp: datetime,
    frame_count: int | None,
    image_path: Path | None,
    thumbnail_path: Path | None,
    video_path: Path | None,
    uploaded_metadata: dict | None = None,
) -> None:
    payload = {
        "incident_id": incident_folder_id,
        "detection_type": incident_type,
        "confidence": confidence,
        "timestamp": timestamp.isoformat(),
        "frame_count": int(frame_count or (uploaded_metadata or {}).get("frame_count") or 0),
        "video_path": str(video_path) if video_path else None,
        "image_path": str(image_path) if image_path else None,
        "files": {
            "frame_1": str(image_path) if image_path else None,
            "thumbnail": str(thumbnail_path) if thumbnail_path else None,
            "incident_video": str(video_path) if video_path else None,
        },
        "ai_metadata": uploaded_metadata or {},
    }
    _write_json(metadata_path, payload)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _next_numbered_path(folder: Path, prefix: str, suffix: str) -> Path:
    for index in range(1, 10000):
        candidate = folder / f"{prefix}_{index}{suffix}"
        if not candidate.exists():
            return candidate
    return folder / f"{prefix}_{int(datetime.utcnow().timestamp())}{suffix}"


def _safe_incident_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if not re.fullmatch(r"incident_\d{8}_\d{6}(?:_\d+)?", value):
        return datetime.utcnow().strftime("incident_%Y%m%d_%H%M%S")
    return value


def _print_received(prefix: str, path: Path) -> None:
    message = f"{prefix} {path} size={path.stat().st_size}"
    print(message)
    logger.info(message)
