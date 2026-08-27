"""Provider for camera metadata and online status."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from agents.context.schemas import CameraContext
from agents.context.exceptions import ProviderError


class CameraProvider:
    """Fetches camera configuration and runtime status from the database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or r"C:\Programs\codex\SheGuard\SheGuard_Backend\sheguard.db"
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            url = f"sqlite:///{self.db_path}"
            self._engine = create_engine(url, connect_args={"check_same_thread": False})
        return self._engine

    def get_camera(self, camera_id: Optional[str]) -> CameraContext:
        if not camera_id:
            return CameraContext()
        try:
            with Session(self._get_engine()) as db:
                # Use raw SQL since we don\'t have the ORM model
                if camera_id.isdigit():
                    result = db.execute(text("SELECT camera_id, camera_name, latitude, longitude, online_status FROM cctv_cameras WHERE camera_id = :id"), {"id": int(camera_id)}).fetchone()
                else:
                    result = db.execute(text("SELECT camera_id, camera_name, latitude, longitude, online_status FROM cctv_cameras WHERE camera_name = :name"), {"name": camera_id}).fetchone()
                
                if result:
                    return CameraContext(
                        id=str(result[0]),
                        name=result[1],
                        zone=None,
                        latitude=result[2],
                        longitude=result[3],
                        online_status=result[4],
                    )
        except Exception as e:
            raise ProviderError("camera", str(e), {"camera_id": camera_id})
        return CameraContext(id=camera_id)
