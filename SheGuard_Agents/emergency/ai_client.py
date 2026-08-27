"""SheGuard_AI coordination.

SheGuard_AI (main.py --source N) is a standalone CV pipeline that publishes its
results as incidents to the backend - there is no HTTP API on the AI process
itself. The orchestrator therefore coordinates with the AI in two ways:

1. Passive (always on): AI incidents arriving via the backend realtime feed
   (`incident.created` with types fall/attack/fight/...) are matched to active
   emergencies by proximity / user and treated as AI_ALERT evidence.
2. Active (optional): if SHEGUARD_AI_URL is configured, an analysis request is
   POSTed best-effort. Failures are logged and NEVER block or fail an
   emergency - the emergency remains ACTIVE without AI.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from emergency.config import EmergencyConfig, get_emergency_config
from emergency.models import CameraAssociation, SessionContext, StandardEvent
from emergency.cctv_locator import haversine_meters

logger = logging.getLogger("sheguard.agents.ai")

# Distance at which an unsolicited AI incident is attached to an emergency.
PROXIMITY_MATCH_METERS = 150.0


class AICoordinator:
    def __init__(self, config: Optional[EmergencyConfig] = None) -> None:
        self.config = config or get_emergency_config()
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        if self.config.ai_available and self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.request_timeout_seconds)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request_analysis(
        self,
        ctx: SessionContext,
        camera: Optional[CameraAssociation],
    ) -> bool:
        """Ask SheGuard_AI to analyse the relevant stream. Best-effort."""
        ctx.ai_requested = True
        if not self.config.ai_available or self._client is None:
            ctx.degraded["ai"] = True
            ctx.ai_unavailable = True
            logger.info("[AGENT] AI endpoint not configured (%s) - passive mode only", ctx.session_id)
            return False
        payload = {
            "session_id": ctx.session_id,
            "user_id": ctx.user_id,
            "incident_ids": list(ctx.incident_ids),
            "camera_id": camera.camera_id if camera else None,
            "rtsp_url": camera.rtsp_url if camera else None,
            "latitude": ctx.latitude,
            "longitude": ctx.longitude,
            "priority": ctx.threat.threat_level.value if ctx.threat else "HIGH",
        }
        try:
            response = await self._client.post(self.config.ai_base_url + "/analyze", json=payload)
            ok = response.status_code < 400
            if not ok:
                logger.warning("[AGENT] AI analysis request failed: %s", response.status_code)
            return ok
        except Exception as exc:  # noqa: BLE001 - AI failure must never stop SOS
            logger.warning("[AGENT] AI unavailable for %s: %s", ctx.session_id, exc)
            return False

    @staticmethod
    def matches_emergency(ctx: SessionContext, event: StandardEvent) -> bool:
        """Should this AI alert be attached to this emergency?

        Order: explicit session link > same user > geo proximity.
        """
        if event.incident_id and event.incident_id in ctx.incident_ids:
            return True
        if event.user_id is not None and event.user_id == ctx.user_id:
            return True
        if (
            ctx.latitude is not None
            and ctx.longitude is not None
            and event.latitude is not None
            and event.longitude is not None
        ):
            try:
                distance = haversine_meters(ctx.latitude, ctx.longitude, event.latitude, event.longitude)
                return distance <= PROXIMITY_MATCH_METERS
            except Exception:  # noqa: BLE001
                return False
        # No coordinates anywhere: only match through the live local camera.
        return bool(ctx.cameras) and event.source == "sheguard_ai"
