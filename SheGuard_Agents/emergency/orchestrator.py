"""Emergency orchestration for SheGuard Agents.

Coordinates the full pipeline:

    PHONE SOS/HELP -> BACKEND EVENT -> AGENT ORCHESTRATOR
        -> emergency session -> tracking coordination
        -> nearby CCTV association -> AI analysis request
        -> threat prioritization -> POLICE ALERT -> BACKEND -> DASHBOARD

Design rules enforced here:
- Per-session isolation: every emergency lives in its own SessionContext,
  keyed by session_id and indexed by user_id. No global emergency state.
- Idempotency: duplicate events (same event key / incident id) are processed
  exactly once; side-effectful backend writes carry idempotency keys.
- Failure tolerance: AI/CCTV/backend/dashboard failures degrade gracefully and
  NEVER stop an active emergency.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections import deque
from datetime import datetime
from typing import Deque, Dict, List, Optional

from core.event_models import EmergencyState, EventType
from emergency.ai_client import AICoordinator
from emergency.cctv_locator import associate_cameras, best_camera
from emergency.config import EmergencyConfig, get_emergency_config
from emergency.models import CameraAssociation, SessionContext, StandardEvent
from emergency.threat_engine import evaluate
from core.client.backend_client import BackendClient

logger = logging.getLogger("sheguard.agents.orchestrator")

LOG_PREFIX = "[AGENT]"


class EmergencyOrchestrator:
    def __init__(
        self,
        client: Optional[BackendClient] = None,
        ai: Optional[AICoordinator] = None,
        config: Optional[EmergencyConfig] = None,
    ) -> None:
        self.config = config or get_emergency_config()
        self.client = client or BackendClient(self.config)
        self.ai = ai or AICoordinator(self.config)

        self.sessions: Dict[str, SessionContext] = {}
        self._user_active: Dict[int, str] = {}
        self._last_sos_at: Dict[int, datetime] = {}
        self._seen_event_keys: Dict[str, float] = {}

        self.recent_events: Deque[dict] = deque(maxlen=300)

        self._background_tasks = set()
        self._watchdog_task: Optional[asyncio.Task] = None
        self._running = False
        self.started_at: Optional[datetime] = None

    # ------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.started_at = datetime.utcnow()
        await self.client.start()
        await self.ai.start()
        self._watchdog_task = asyncio.create_task(self._watchdog_loop(), name="sheguard-agents-watchdog")
        logger.info("%s Orchestrator started", LOG_PREFIX)

    async def stop(self) -> None:
        self._running = False
        if self._watchdog_task:
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
            except asyncio.CancelledError:
                pass
            self._watchdog_task = None
        for ctx in self.sessions.values():
            self._cancel_help_timer(ctx)
        for task in list(self._background_tasks):
            task.cancel()
        await self.client.stop()
        await self.ai.stop()
        logger.info("%s Orchestrator stopped", LOG_PREFIX)

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    # ---------------------------------------------------------- event entry
    async def handle_event(self, event: StandardEvent) -> bool:
        """Main entry point for every standard event. Returns True if processed."""
        key = event.key()
        if self._is_duplicate(key):
            logger.debug("%s Duplicate event skipped: %s", LOG_PREFIX, key)
            self._log(event, duplicate=True)
            return False

        self._log(event)
        handler = {
            EventType.SOS_TRIGGERED: self._on_sos,
            EventType.HELP_TRIGGERED: self._on_help,
            EventType.HELP_CANCELLED: self._on_help_cancelled,
            EventType.EMERGENCY_CREATED: self._on_emergency_created,
            EventType.LOCATION_UPDATED: self._on_location,
            EventType.TRACKING_UPDATED: self._on_location,
            EventType.TRACKING_STOPPED: self._on_tracking_stopped,
            EventType.AI_ALERT: self._on_ai_alert,
            EventType.INCIDENT_ACKNOWLEDGED: self._on_acknowledged,
            EventType.INCIDENT_ASSIGNED: self._on_assigned,
            EventType.INCIDENT_RESOLVED: self._on_resolved,
            EventType.NETWORK_OFFLINE: self._on_network_offline,
            EventType.NETWORK_RECOVERED: self._on_network_recovered,
        }.get(event.event_type)

        if handler is None:
            return False
        try:
            result = await handler(event)
            return True if not isinstance(result, bool) else result
        except Exception as exc:  # noqa: BLE001 - malformed/handlers must not crash
            logger.error("%s Error handling %s: %s", LOG_PREFIX, event.event_type, exc, exc_info=True)
            return False

    # ------------------------------------------------------------ dedupe/log
    def _is_duplicate(self, key: str) -> bool:
        import time

        now = time.monotonic()
        ttl = self.config.idempotency_ttl_seconds
        self._seen_event_keys = {k: ts for k, ts in self._seen_event_keys.items() if now - ts < ttl}
        if not key:
            return False
        if key in self._seen_event_keys:
            return True
        self._seen_event_keys[key] = now
        return False

    def _log(self, event: StandardEvent, duplicate: bool = False) -> None:
        self.recent_events.appendleft(
            {
                "event_type": event.event_type.value,
                "user_id": event.user_id,
                "session_id": event.session_id,
                "incident_id": event.incident_id,
                "source": event.source,
                "duplicate": duplicate,
                "at": datetime.utcnow().isoformat(),
            }
        )
        logger.info(
            "%s Event %s user=%s session=%s incident=%s src=%s%s",
            LOG_PREFIX,
            event.event_type.value,
            event.user_id,
            event.session_id,
            event.incident_id,
            event.source,
            " (dup)" if duplicate else "",
        )

    # ------------------------------------------------------------------ SOS
    async def _on_sos(self, event: StandardEvent) -> bool:
        user_id = event.user_id
        if user_id is None:
            logger.warning("%s SOS without user_id dropped", LOG_PREFIX)
            return False

        # Existing active emergency for this user? Never create duplicates.
        existing_sid = self._user_active.get(user_id)
        if existing_sid:
            ctx = self.sessions.get(existing_sid)
            if ctx and ctx.is_active:
                if event.incident_id and event.incident_id in ctx.incident_ids:
                    return  # exact duplicate
                now = datetime.utcnow()
                last = self._last_sos_at.get(user_id)
                within_window = last is not None and (now - last).total_seconds() <= self.config.duplicate_sos_window_seconds
                if not within_window:
                    ctx.repeated_alerts += 1
                ctx.incident_ids.append(event.incident_id) if event.incident_id else None
                if event.latitude is not None:
                    ctx.latitude = event.latitude
                    ctx.longitude = event.longitude
                    ctx.last_location_at = now
                logger.info(
                    "%s Repeated SOS attached to active emergency %s (repeats=%d)",
                    LOG_PREFIX,
                    ctx.session_id,
                    ctx.repeated_alerts,
                )
                self._reevaluate_threat(ctx)
                self._spawn(self._push_state(ctx, note="repeated_sos"))
                return

        # Fresh emergency - resolve identity/location before creating context.
        location = await self._fetch_location(user_id)
        session_id = (event.session_id or (location or {}).get("session_id") or "") or f"sg-{uuid.uuid4().hex[:12]}"
        if session_id in self.sessions and self.sessions[session_id].is_terminal:
            session_id = f"sg-{uuid.uuid4().hex[:12]}"

        ctx = SessionContext(session_id=session_id, user_id=user_id)
        ctx.trigger = "HELP" if (event.incident_type or "").lower() == "help" else "SOS"
        ctx.silent = bool(getattr(event, "silent", False))
        ctx.trigger_source = event.incident_type or ("silent_sos" if ctx.silent else "manual_sos")
        if event.incident_id:
            ctx.incident_ids.append(event.incident_id)
        if event.latitude is not None:
            ctx.latitude, ctx.longitude = event.latitude, event.longitude
            ctx.last_location_at = datetime.utcnow()
        elif location:
            ctx.latitude = location.get("latitude")
            ctx.longitude = location.get("longitude")
            ctx.last_location_at = _parse_dt(location.get("timestamp"))
            if not event.session_id and location.get("session_id"):
                session_id = str(location["session_id"])
                ctx.session_id = session_id

        self.sessions[session_id] = ctx
        self._user_active[user_id] = session_id
        self._last_sos_at[user_id] = datetime.utcnow()
        ctx.transition(EmergencyState.EMERGENCY_CREATED, force=True)
        logger.info(
            "%s Emergency received | User: %s | Session: %s | Location: %s,%s",
            LOG_PREFIX,
            user_id,
            session_id,
            ctx.latitude,
            ctx.longitude,
        )
        self._spawn(self._pipeline(ctx))

    async def _on_help(self, event: StandardEvent) -> None:
        """HELP_PENDING -> 5s window -> CANCELLED or EMERGENCY."""
        user_id = event.user_id
        if user_id is None:
            return
        existing_sid = self._user_active.get(user_id)
        if existing_sid and self.sessions.get(existing_sid) and self.sessions[existing_sid].is_active:
            return  # already handled as active emergency

        session_id = event.session_id or f"sg-help-{uuid.uuid4().hex[:12]}"
        ctx = SessionContext(session_id=session_id, user_id=user_id)
        ctx.trigger = "HELP"
        ctx.trigger_source = "help_pending"
        if event.incident_id:
            ctx.incident_ids.append(event.incident_id)
        ctx.latitude, ctx.longitude = event.latitude, event.longitude
        self.sessions[session_id] = ctx
        ctx.transition(EmergencyState.HELP_PENDING, force=True)
        logger.info("%s HELP pending (%ss window) user=%s session=%s", LOG_PREFIX, self.config.help_timeout_seconds, user_id, session_id)

        async def _timeout():
            try:
                await asyncio.sleep(self.config.help_timeout_seconds)
            except asyncio.CancelledError:
                raise
            if ctx.state is EmergencyState.HELP_PENDING:
                logger.info("%s HELP window expired -> emergency activation user=%s", LOG_PREFIX, user_id)
                ctx.transition(EmergencyState.EMERGENCY_CREATED, force=True)
                self._user_active.setdefault(user_id, session_id)
                self._last_sos_at[user_id] = datetime.utcnow()
                self._spawn(self._pipeline(ctx))

        ctx.help_timer_handle = asyncio.create_task(_timeout())

    async def _on_help_cancelled(self, event: StandardEvent) -> None:
        sid = self._user_active.get(event.user_id or -1)
        ctx = self.sessions.get(event.session_id or "") or self.sessions.get(sid or "")
        if not ctx or ctx.state is not EmergencyState.HELP_PENDING:
            return
        self._cancel_help_timer(ctx)
        ctx.transition(EmergencyState.CANCELLED, force=True)
        ctx.resolution = "cancelled_by_user"
        self._user_active.pop(ctx.user_id, None)
        logger.info("%s HELP cancelled by user=%s session=%s", LOG_PREFIX, ctx.user_id, ctx.session_id)

    @staticmethod
    def _cancel_help_timer(ctx: SessionContext) -> None:
        handle = ctx.help_timer_handle
        if handle is not None:
            handle.cancel()
            ctx.help_timer_handle = None

    # ------------------------------------------------------------- pipeline
    async def _fetch_location(self, user_id: int) -> Optional[dict]:
        """Latest known location for a user (public backend endpoint)."""
        result = await self.client.get_live_location(user_id)
        if result.ok and isinstance(result.data, dict):
            return result.data
        return None

    async def _pipeline(self, ctx: SessionContext) -> None:
        """Full orchestration for one emergency. Every step degrades safely."""
        try:
            # 1) Ensure backend emergency session exists (idempotent).
            await self._ensure_backend_session(ctx)

            # 2) Tracking coordination.
            await self._coordinate_tracking(ctx)

            # 3) Nearby CCTV association.
            await self._associate_cctv(ctx)

            # 4) AI analysis request (non-blocking, optional).
            await self._request_ai(ctx)

            # 5) Threat prioritization.
            self._reevaluate_threat(ctx)

            # 6) Police alert.
            await self._publish_police_alert(ctx)

            logger.info(
                "%s Pipeline complete %s | state=%s threat=%s cctv=%d ai=%s",
                LOG_PREFIX,
                ctx.session_id,
                ctx.state.value,
                ctx.threat.threat_level.value if ctx.threat else "-",
                len(ctx.cameras),
                ctx.ai_result or ("unavailable" if ctx.ai_unavailable else "pending"),
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - emergency must survive bugs
            logger.error("%s Pipeline error %s: %s", LOG_PREFIX, ctx.session_id, exc, exc_info=True)
            ctx.degraded["pipeline"] = True
            self._spawn(self._push_state(ctx, note=f"error:{exc}"))

    async def _ensure_backend_session(self, ctx: SessionContext) -> None:
        if ctx.backend_session_created:
            return
        result = await self.client.create_emergency_session(
            user_id=ctx.user_id,
            session_id=ctx.session_id,
            incident_id=ctx.incident_ids[0] if ctx.incident_ids else None,
            latitude=ctx.latitude,
            longitude=ctx.longitude,
            trigger_source=ctx.trigger_source or "agent_orchestrator",
            idempotency_key=ctx.session_id,
        )
        if result.ok:
            ctx.backend_session_created = True
            logger.info("%s Backend emergency session ready: %s", LOG_PREFIX, ctx.session_id)
        else:
            ctx.degraded["backend"] = True
            logger.warning("%s Backend session create deferred for %s (%s)", LOG_PREFIX, ctx.session_id, result.error)

    async def _coordinate_tracking(self, ctx: SessionContext) -> None:
        ctx.transition(EmergencyState.TRACKING_STARTING, force=True)
        result = await self.client.get_tracking_live(ctx.session_id)
        if result.ok and isinstance(result.data, dict):
            ctx.tracking_active = bool(result.data.get("active"))
            latest = result.data.get("latest") or {}
            if latest.get("latitude") is not None and ctx.latitude is None:
                ctx.latitude = latest.get("latitude")
                ctx.longitude = latest.get("longitude")
                ctx.last_location_at = _parse_dt(latest.get("timestamp"))
        else:
            # The phone always starts tracking before the incident reaches us;
            # treat tracking as presumed-active rather than failing.
            ctx.tracking_active = True
            ctx.degraded["tracking_check"] = True
        ctx.transition(EmergencyState.TRACKING_ACTIVE, force=True)
        logger.info(
            "%s Tracking %s | session=%s user=%s",
            LOG_PREFIX,
            "active" if ctx.tracking_active else "unconfirmed",
            ctx.session_id,
            ctx.user_id,
        )

    async def _associate_cctv(self, ctx: SessionContext) -> None:
        ctx.transition(EmergencyState.CCTV_SEARCH, force=True)
        cameras_result = await self.client.list_cameras()
        cameras: List[dict] = []
        if cameras_result.ok and isinstance(cameras_result.data, dict):
            cameras = cameras_result.data.get("cameras") or []
        else:
            ctx.degraded["cctv_registry"] = True
            logger.warning("%s CCTV registry unavailable (%s)", LOG_PREFIX, cameras_result.error)

        ctx.cameras = associate_cameras(
            cameras,
            ctx.latitude,
            ctx.longitude,
            max_distance_meters=self.config.max_cctv_distance_meters,
            max_cameras=self.config.max_cameras_per_emergency,
        )
        chosen = best_camera(ctx.cameras)
        if chosen:
            logger.info(
                "%s Nearby CCTV search | %s selected (%s, %.0fm)",
                LOG_PREFIX,
                chosen.camera_name,
                chosen.online_status,
                chosen.distance_meters or -1,
            )
        else:
            logger.info("%s Nearby CCTV search | no geo-matched camera for %s", LOG_PREFIX, ctx.session_id)

    async def _request_ai(self, ctx: SessionContext) -> None:
        camera = best_camera(ctx.cameras)
        ctx.transition(EmergencyState.AI_ANALYSIS, force=True)
        ok = await self.ai.request_analysis(ctx, camera)
        if not ok:
            ctx.ai_unavailable = True
            ctx.degraded["ai"] = True
            logger.info("%s AI analysis unavailable - emergency remains ACTIVE (%s)", LOG_PREFIX, ctx.session_id)
        # Return to tracking state; AI results arrive asynchronously as alerts.
        ctx.transition(EmergencyState.TRACKING_ACTIVE, force=True)

    def _reevaluate_threat(self, ctx: SessionContext) -> None:
        previous_level = ctx.threat.threat_level if ctx.threat else None
        ctx.threat = evaluate(ctx)
        current = ctx.threat.threat_level
        if current != previous_level:
            logger.info(
                "%s Priority: %s (score %.0f) session=%s",
                LOG_PREFIX,
                current.value,
                ctx.threat.score,
                ctx.session_id,
            )

    async def _publish_police_alert(self, ctx: SessionContext, force: bool = False) -> None:
        if ctx.police_alerted and not force:
            return
        if ctx.threat is None:
            self._reevaluate_threat(ctx)
        result = await self.client.police_alert(
            {
                "incident_id": ctx.incident_ids[0] if ctx.incident_ids else None,
                "session_id": ctx.session_id,
                "user_id": ctx.user_id,
                "threat_level": ctx.threat.threat_level.value,
                "priority_score": ctx.threat.score,
                "message": f"[{ctx.threat.threat_level.value}] {ctx.trigger} emergency | "
                f"user={ctx.user_id} session={ctx.session_id} | "
                f"reasons={'; '.join(ctx.threat.reasons)}",
                "cameras": [c.to_dict() for c in ctx.cameras],
            },
            idempotency_key=f"{ctx.session_id}:{ctx.threat.threat_level.value}",
        )
        if result.ok:
            was_already = ctx.police_alerted
            ctx.police_alerted = True
            ctx.transition(EmergencyState.POLICE_ALERTED, force=True)
            if not was_already:
                logger.info("%s Police alert published | session=%s level=%s", LOG_PREFIX, ctx.session_id, ctx.threat.threat_level.value)
        else:
            ctx.degraded["police_alert"] = True
            logger.warning("%s Police alert publish failed for %s (%s)", LOG_PREFIX, ctx.session_id, result.error)

    async def _push_state(self, ctx: SessionContext, note: Optional[str] = None) -> None:
        """Mirror orchestration state into the backend so the dashboard can show it."""
        payload = {
            "incident_id": ctx.incident_ids[0] if ctx.incident_ids else None,
            "session_id": ctx.session_id,
            "state": ctx.state.value,
            "threat_level": ctx.threat.threat_level.value if ctx.threat else None,
            "threat_score": ctx.threat.score if ctx.threat else None,
            "priority": ctx.threat.threat_level.value if ctx.threat else None,
            "ai_result": ctx.ai_result,
            "ai_confidence": ctx.ai_confidence,
            "ai_unavailable": ctx.ai_unavailable or None,
            "tracking_status": "active" if ctx.tracking_active else "stale" if ctx.stale_notified else None,
            "cameras": [c.to_dict() for c in ctx.cameras] or None,
            "timeline_event": {"note": note} if note else None,
            "metadata": {
                "trigger": ctx.trigger,
                "silent": ctx.silent,
                "repeated_alerts": ctx.repeated_alerts,
                "duration_seconds": round(ctx.duration_seconds(), 1),
            },
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        result = await self.client.push_agent_state(payload)
        if not result.ok:
            logger.debug("%s State push deferred for %s (%s)", LOG_PREFIX, ctx.session_id, result.error)

    # ------------------------------------------------------ location/tracking
    async def _on_location(self, event: StandardEvent) -> None:
        ctx = self._resolve_context(event)
        if ctx is None or not ctx.is_active:
            return
        # Adopt the phone's real session id if we generated one earlier.
        if (
            event.session_id
            and ctx.session_id != event.session_id
            and not ctx.backend_session_created
            and ctx.state not in (EmergencyState.HELP_PENDING,)
        ):
            self._adopt_session_id(ctx, event.session_id)
        if event.latitude is not None:
            ctx.latitude = event.latitude
            ctx.longitude = event.longitude
            ctx.accuracy = event.accuracy
            ctx.last_location_at = event.timestamp or datetime.utcnow()
        if not ctx.tracking_active:
            ctx.tracking_active = True
        if ctx.stale_notified:
            ctx.stale_notified = False
            logger.info("%s Tracking recovered for %s", LOG_PREFIX, ctx.session_id)
        self._spawn(self._push_state(ctx, note="location_updated"))

    def _resolve_context(self, event: StandardEvent) -> Optional[SessionContext]:
        if event.session_id and event.session_id in self.sessions:
            return self.sessions[event.session_id]
        if event.user_id is not None:
            sid = self._user_active.get(event.user_id)
            if sid and sid in self.sessions:
                return self.sessions[sid]
        return None

    def _adopt_session_id(self, ctx: SessionContext, new_sid: str) -> None:
        self.sessions.pop(ctx.session_id, None)
        old_sid = ctx.session_id
        ctx.session_id = new_sid
        self.sessions[new_sid] = ctx
        if self._user_active.get(ctx.user_id) == old_sid:
            self._user_active[ctx.user_id] = new_sid
        logger.info("%s Adopted phone session id %s (was %s)", LOG_PREFIX, new_sid, old_sid)

    async def _on_tracking_stopped(self, event: StandardEvent) -> None:
        ctx = self._resolve_context(event)
        if ctx and ctx.is_active:
            ctx.tracking_active = False
            logger.info("%s Tracking stopped for %s", LOG_PREFIX, ctx.session_id)

    async def _on_emergency_created(self, event: StandardEvent) -> None:
        ctx = self._resolve_context(event)
        if ctx is None and event.session_id and event.user_id is not None:
            # Emergency created elsewhere (auto-SOS path) without an SOS event.
            ctx = SessionContext(session_id=event.session_id, user_id=event.user_id)
            ctx.latitude, ctx.longitude = event.latitude, event.longitude
            ctx.backend_session_created = True
            self.sessions[event.session_id] = ctx
            self._user_active.setdefault(event.user_id, event.session_id)
            ctx.transition(EmergencyState.EMERGENCY_CREATED, force=True)
            logger.info("%s External emergency observed: %s", LOG_PREFIX, event.session_id)
            self._spawn(self._pipeline(ctx))
        elif ctx:
            ctx.backend_session_created = True

    # ------------------------------------------------------------------ AI
    async def _on_ai_alert(self, event: StandardEvent) -> None:
        matched = False
        for ctx in list(self.sessions.values()):
            if not ctx.is_active:
                continue
            if self.ai.matches_emergency(ctx, event):
                matched = True
                if event.incident_id and event.incident_id not in ctx.incident_ids:
                    ctx.incident_ids.append(event.incident_id)
                ctx.ai_result = event.ai_result
                ctx.ai_confidence = event.confidence
                ctx.ai_requested = True
                if event.latitude is not None and ctx.latitude is None:
                    ctx.latitude, ctx.longitude = event.latitude, event.longitude
                logger.info(
                    "%s AI result: %s | Confidence: %.2f | session=%s",
                    LOG_PREFIX,
                    event.ai_result,
                    event.confidence,
                    ctx.session_id,
                )
                self._reevaluate_threat(ctx)
                # Escalate police alert if the level increased.
                await self._publish_police_alert(ctx, force=False)
                self._spawn(self._push_state(ctx, note="ai_alert"))
                break
        if not matched:
            logger.info("%s AI alert %s had no matching active emergency (standalone incident kept in backend)", LOG_PREFIX, event.ai_result)
            return False
        return True

    # ------------------------------------------------------- police actions
    async def _on_acknowledged(self, event: StandardEvent) -> None:
        ctx = self._resolve_context(event)
        if ctx:
            ctx.transition(EmergencyState.POLICE_RESPONDING, force=True)
            logger.info("%s Incident acknowledged session=%s", LOG_PREFIX, ctx.session_id)

    async def _on_assigned(self, event: StandardEvent) -> None:
        ctx = self._resolve_context(event)
        if ctx:
            ctx.transition(EmergencyState.POLICE_RESPONDING, force=True)
            logger.info("%s Unit responding session=%s", LOG_PREFIX, ctx.session_id)

    async def _on_resolved(self, event: StandardEvent) -> None:
        ctx = self._resolve_context(event)
        if ctx and ctx.is_active:
            ctx.resolved_at = datetime.utcnow()
            ctx.resolution = event.status or "resolved"
            ctx.transition(EmergencyState.EMERGENCY_RESOLVED, force=True)
            self._user_active.pop(ctx.user_id, None)
            logger.info("%s Emergency RESOLVED session=%s user=%s", LOG_PREFIX, ctx.session_id, ctx.user_id)

    # -------------------------------------------------------------- network
    async def _on_network_offline(self, event: StandardEvent) -> None:
        logger.warning("%s Network offline - buffering publishes, emergencies stay ACTIVE", LOG_PREFIX)
        for ctx in self.sessions.values():
            if ctx.is_active:
                ctx.degraded["network"] = True

    async def _on_network_recovered(self, event: StandardEvent) -> None:
        logger.info("%s Network recovered - flushing outbox and reconciling", LOG_PREFIX)
        flushed = await self.client.flush_outbox()
        if flushed:
            logger.info("%s Outbox flushed: %d publish(es)", LOG_PREFIX, flushed)
        for ctx in self.sessions.values():
            ctx.degraded.pop("network", None)
            if ctx.is_active and not ctx.backend_session_created:
                self._spawn(self._ensure_backend_session(ctx))
        # Pick up anything missed while disconnected.
        self._spawn(self._reconcile())

    async def _reconcile(self) -> None:
        snapshot = await self.client.agent_live_snapshot()
        if not snapshot.ok or not isinstance(snapshot.data, dict):
            return
        known = {ctx.session_id for ctx in self.sessions.values()}
        for sess in snapshot.data.get("emergency_sessions") or []:
            sid = sess.get("session_id")
            uid = sess.get("user_id")
            if sid and sid not in known and uid is not None and not any(c.user_id == uid and c.is_active for c in self.sessions.values()):
                ctx = SessionContext(session_id=str(sid), user_id=int(uid))
                ctx.backend_session_created = True
                ctx.latitude, ctx.longitude = sess.get("latitude"), sess.get("longitude")
                self.sessions[str(sid)] = ctx
                self._user_active.setdefault(int(uid), str(sid))
                ctx.transition(EmergencyState.EMERGENCY_CREATED, force=True)
                logger.info("%s Reconciled external emergency %s", LOG_PREFIX, sid)
                self._spawn(self._pipeline(ctx))

    # ------------------------------------------------------------- watchdog
    async def _watchdog_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.config.stale_check_interval_seconds)
                await self._check_stale_tracking()
                await self._escalate_long_running()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("%s Watchdog error: %s", LOG_PREFIX, exc)

    async def _check_stale_tracking(self) -> None:
        now = datetime.utcnow()
        threshold = self.config.tracking_stale_seconds
        for ctx in list(self.sessions.values()):
            if not ctx.is_active or not ctx.tracking_active or ctx.stale_notified:
                continue
            if ctx.last_location_at is None:
                continue  # never had a fix - avoid false alarms
            silent_for = (now - ctx.last_location_at).total_seconds()
            if silent_for < threshold:
                continue
            # Confirm against backend before flagging (avoid tiny timing noise).
            fresh = await self.client.get_live_location(ctx.user_id)
            fresh_ts = _parse_dt((fresh.data or {}).get("timestamp")) if fresh.ok and isinstance(fresh.data, dict) else None
            if fresh_ts and fresh_ts > ctx.last_location_at:
                ctx.latitude = (fresh.data or {}).get("latitude")
                ctx.longitude = (fresh.data or {}).get("longitude")
                ctx.last_location_at = fresh_ts
                continue
            ctx.stale_notified = True
            logger.warning("%s TRACKING_STALE session=%s user=%s (no GPS for %.0fs)", LOG_PREFIX, ctx.session_id, ctx.user_id, silent_for)
            self.recent_events.appendleft(
                {"event_type": "TRACKING_STALE", "user_id": ctx.user_id, "session_id": ctx.session_id, "at": now.isoformat()}
            )
            self._spawn(self._push_state(ctx, note=f"tracking_stale_{int(silent_for)}s"))

    async def _escalate_long_running(self) -> None:
        for ctx in list(self.sessions.values()):
            if not ctx.is_active or ctx.threat is None:
                continue
            if ctx.duration_seconds() >= 60 and int(ctx.duration_seconds()) % 60 < self.config.stale_check_interval_seconds + 1:
                previous_score = ctx.threat.score
                self._reevaluate_threat(ctx)
                if ctx.threat.score > previous_score and not ctx.police_alerted:
                    await self._publish_police_alert(ctx)
                elif ctx.threat.score > previous_score:
                    self._spawn(self._push_state(ctx, note="threat_escalated"))

    # ------------------------------------------------------------- queries
    def active_sessions(self) -> List[SessionContext]:
        return [ctx for ctx in self.sessions.values() if ctx.is_active]

    def snapshot(self) -> dict:
        sessions = sorted(self.sessions.values(), key=lambda c: c.created_at)
        return {
            "orchestrator": "RUNNING" if self._running else "STOPPED",
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "active_count": len(self.active_sessions()),
            "backend": {
                "breaker_open": self.client.breaker_open,
                "outbox_size": self.client.outbox_size,
            },
            "sessions": [ctx.to_dict() for ctx in sessions],
            "recent_events": list(self.recent_events)[:50],
        }

    def get_session(self, session_id: str) -> Optional[SessionContext]:
        return self.sessions.get(session_id)


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None
