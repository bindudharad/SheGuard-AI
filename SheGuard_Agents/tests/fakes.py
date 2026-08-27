"""Shared fakes for emergency orchestrator tests."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.client.backend_client import ClientResult
from emergency.models import CameraAssociation


class FakeBackendClient:
    """In-memory stand-in for BackendClient - fully offline & deterministic."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.cameras: List[dict] = []
        self.tracking: Dict[str, dict] = {}
        self.locations: Dict[int, dict] = {}
        self.fail_next_police_alerts = 0
        self.emergency_creates = 0
        self.police_alerts = 0
        self.outbox_items: List[dict] = []

    async def start(self):
        pass

    async def stop(self):
        pass

    @property
    def breaker_open(self):
        return False

    @property
    def outbox_size(self):
        return len(self.outbox_items)

    async def create_emergency_session(self, user_id, session_id, incident_id, latitude, longitude, trigger_source, idempotency_key=None):
        self.emergency_creates += 1
        self.calls.append(("emergency", user_id, session_id))
        return ClientResult(ok=True, data={"session_id": session_id})

    async def get_tracking_live(self, session_id):
        data = self.tracking.get(session_id)
        if data is None:
            return ClientResult(ok=False, error="404")
        return ClientResult(ok=True, data=data)

    async def get_live_location(self, user_id):
        data = self.locations.get(user_id)
        if data is None:
            return ClientResult(ok=False, error="404")
        return ClientResult(ok=True, data=data)

    async def list_cameras(self):
        if self.cameras:
            return ClientResult(ok=True, data={"count": len(self.cameras), "cameras": self.cameras})
        return ClientResult(ok=False, error="unavailable")

    async def push_agent_state(self, payload, idempotency_key=None):
        self.calls.append(("state", payload.get("session_id"), payload.get("state")))
        return ClientResult(ok=True)

    async def police_alert(self, payload, idempotency_key=None):
        if self.fail_next_police_alerts > 0:
            self.fail_next_police_alerts -= 1
            self.outbox_items.append({"key": idempotency_key})
            return ClientResult(ok=False, error="backend down")
        self.police_alerts += 1
        self.calls.append(("police", payload.get("session_id"), payload.get("threat_level")))
        return ClientResult(ok=True, data={"alert": payload})

    async def resolve_emergency(self, session_id):
        self.calls.append(("resolve", session_id))
        return ClientResult(ok=True)

    async def acknowledge_emergency(self, session_id):
        return ClientResult(ok=True)

    async def flush_outbox(self):
        n = len(self.outbox_items)
        self.outbox_items.clear()
        return n

    async def agent_live_snapshot(self):
        return ClientResult(ok=False, error="not used in most tests")

    # helpers -----------------------------------------------------------
    def add_camera(self, camera_id, lat, lon, online="online", name=None, distance_hint=None):
        self.cameras.append(
            {
                "camera_id": camera_id,
                "camera_name": name or f"Camera-{camera_id}",
                "latitude": lat,
                "longitude": lon,
                "online_status": online,
                "rtsp_url": f"rtsp://cam{camera_id}" if online == "online" else None,
            }
        )


def make_camera(camera_id: int, distance_meters: float, online: str = "online") -> CameraAssociation:
    return CameraAssociation(
        camera_id=camera_id,
        camera_name=f"Camera-{camera_id}",
        distance_meters=distance_meters,
        online_status=online,
        rtsp_url=f"rtsp://cam{camera_id}" if online == "online" else None,
    )
