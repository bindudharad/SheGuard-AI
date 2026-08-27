from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas import CameraCreate
from backend.database import get_db
from backend.models import CCTVCamera
from backend.services.camera_manager import CameraManager


router = APIRouter(tags=["cctv"])
camera_manager = CameraManager()


def camera_out(row: CCTVCamera) -> dict:
    return {
        "camera_id": row.camera_id,
        "camera_name": row.camera_name,
        "ip_address": row.ip_address,
        "rtsp_url": row.rtsp_url,
        "latitude": row.latitude,
        "longitude": row.longitude,
        "online_status": row.online_status,
    }


@router.post("/camera/register")
def register_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    camera = CCTVCamera(**payload.dict())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera_out(camera)


@router.get("/camera/list")
def list_cameras(db: Session = Depends(get_db)):
    rows = db.scalars(select(CCTVCamera).order_by(CCTVCamera.camera_id.desc())).all()
    return {"count": len(rows), "cameras": [camera_out(row) for row in rows]}


@router.get("/camera/health")
def camera_health(db: Session = Depends(get_db)):
    rows = db.scalars(select(CCTVCamera).order_by(CCTVCamera.camera_id.desc())).all()
    registered = [camera_out(row) for row in rows]
    return {"registered": registered, "runtime": camera_manager.status()}
