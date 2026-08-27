"""Reconnecting WebSocket client for the backend realtime hub (/ws/live).

Converts raw backend broadcasts into StandardEvents and hands them to the
orchestrator. Auto-reconnects with capped exponential backoff and reports
NETWORK_OFFLINE / NETWORK_RECOVERED transitions.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import websockets

from emergency.config import EmergencyConfig, get_emergency_config
from emergency.models import EventType, StandardEvent, is_sos_incident, map_ai_incident

logger = logging.getLogger("sheguard.agents.ws")

Handler = Callable[[StandardEvent], Awaitable[None]]

# Backend realtime event name -> standard event type
EVENT_MAP = {
    "incident.created": EventType.SOS_TRIGGERED,  # refined in parse_raw_message
    "emergency.started": EventType.EMERGENCY_CREATED,
    "tracking_update": EventType.LOCATION_UPDATED,
    "emergency.acknowledged": EventType.INCIDENT_ACKNOWLEDGED,
    "emergency.responding": EventType.INCIDENT_ASSIGNED,
    "emergency.resolved": EventType.INCIDENT_RESOLVED,
}


class LiveEventClient:
    def __init__(self, handler: Handler, config: Optional[EmergencyConfig] = None) -> None:
        self.config = config or get_emergency_config()
        self._handler = handler
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.connected = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="sheguard-agents-ws")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                pass
            self._task = None

    async def _run_loop(self) -> None:
        delay = self.config.ws_reconnect_min_seconds
        while self._running:
            try:
                async with websockets.connect(self.config.ws_live_url, open_timeout=5, ping_interval=20) as ws:
                    was_connected = self.connected
                    self.connected = True
                    logger.info("[AGENT] Connected to backend live events")
                    if not was_connected:
                        # Reconnect may have dropped messages - let the
                        # orchestrator reconcile against backend state.
                        await self._dispatch(
                            StandardEvent(event_type=EventType.NETWORK_RECOVERED, source="ws_reconnect")
                        )
                    async for raw in ws:
                        if not self._running:
                            break
                        event = parse_raw_message(raw)
                        if event is not None:
                            await self._dispatch(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - keep retrying forever
                if self.connected:
                    self.connected = False
                    logger.warning("[AGENT] Live events disconnected: %s", exc)
                    await self._dispatch(StandardEvent(event_type=EventType.NETWORK_OFFLINE, source="ws"))
                else:
                    logger.info("[AGENT] Backend live events unavailable (%s); retrying in %.1fs", exc, delay)
            if not self._running:
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.config.ws_reconnect_max_seconds)

    async def _dispatch(self, event: StandardEvent) -> None:
        try:
            await self._handler(event)
        except Exception as exc:  # noqa: BLE001 - one bad event must not kill the loop
            logger.error("[AGENT] Handler error for %s: %s", event.event_type, exc)

    async def consume_once(self, message: str | bytes) -> bool:
        """Process a single raw WS frame (used by tests and simulation)."""
        event = parse_raw_message(message)
        if event is None:
            return False
        await self._dispatch(event)
        return True


def parse_raw_message(message: str | bytes) -> Optional[StandardEvent]:
    """Map a raw /ws/live frame to a StandardEvent. Unknown frames -> None."""
    try:
        data = json.loads(message.decode() if isinstance(message, bytes) else message)
    except (ValueError, UnicodeDecodeError):
        logger.debug("[AGENT] Dropping malformed frame")
        return None
    if not isinstance(data, dict):
        return None

    event_name = str(data.get("event") or "")
    payload = data.get("payload")
    if not isinstance(payload, dict):
        payload = {}

    base_type = EVENT_MAP.get(event_name)

    # --- incident.created: decide SOS vs AI alert from incident_type -------
    if event_name == "incident.created":
        incident = payload.get("incident") if isinstance(payload.get("incident"), dict) else {}
        incident_type = str(payload.get("incident_type") or incident.get("incident_type") or "")
        ai_result = map_ai_incident(incident_type)
        common = dict(
            user_id=_as_int(payload.get("user_id") or incident.get("user_id")),
            incident_id=_as_int(payload.get("incident_id") or incident.get("incident_id")),
            latitude=_as_float(payload.get("latitude") or incident.get("latitude")),
            longitude=_as_float(payload.get("longitude") or incident.get("longitude")),
            incident_type=incident_type.lower() or None,
            metadata={"raw_event": event_name},
        )
        if is_sos_incident(incident_type):
            common["event_type"] = EventType.SOS_TRIGGERED
            common["confidence"] = _as_float(incident.get("confidence"), 1.0) or 1.0
            common["source"] = "app"
            common["silent"] = incident_type.lower() == "silent_sos"
            common["timestamp"] = _parse_ts(payload.get("timestamp")) or datetime.utcnow()
            return StandardEvent(**common)
        if ai_result:
            common["event_type"] = EventType.AI_ALERT
            common["confidence"] = _as_float(incident.get("confidence"), 0.0) or 0.0
            common["camera_id"] = str(incident.get("camera_id") or "") or None
            common["ai_result"] = ai_result
            common["source"] = "sheguard_ai"
            common["timestamp"] = datetime.utcnow()
            return StandardEvent(**common)
        return None

    if base_type is None:
        return None

    if event_name == "tracking_update":
        location = payload.get("location") if isinstance(payload.get("location"), dict) else {}
        session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
        return StandardEvent(
            event_type=EventType.LOCATION_UPDATED,
            user_id=_as_int(payload.get("user_id") or session.get("user_id")),
            session_id=str(payload.get("session_id") or session.get("session_id") or "") or None,
            latitude=_as_float(location.get("latitude")),
            longitude=_as_float(location.get("longitude")),
            accuracy=_as_float(location.get("accuracy")),
            speed=_as_float(location.get("speed")),
            battery=_as_int(location.get("battery")),
            timestamp=_parse_ts(location.get("timestamp")) or datetime.utcnow(),
            source="phone",
            event_id=f"loc:{location.get('location_id')}" if location.get("location_id") else None,
        )

    if event_name == "emergency.started":
        return StandardEvent(
            event_type=EventType.EMERGENCY_CREATED,
            user_id=_as_int(payload.get("user_id")),
            session_id=str(payload.get("session_id") or "") or None,
            incident_id=_as_int(payload.get("incident_id")),
            latitude=_as_float(payload.get("latitude")),
            longitude=_as_float(payload.get("longitude")),
            status=payload.get("status"),
            source="backend",
        )

    return StandardEvent(
        event_type=base_type,
        user_id=_as_int(payload.get("user_id")),
        session_id=str(payload.get("session_id") or "") or None,
        incident_id=_as_int(payload.get("incident_id")),
        status=payload.get("status"),
        source="backend",
    )


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_int(value) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_float(value, default=None):
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _parse_ts(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except (ValueError, TypeError):
        return None
