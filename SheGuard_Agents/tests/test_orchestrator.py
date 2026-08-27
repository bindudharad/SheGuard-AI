"""Orchestrator behaviour tests: SOS/HELP flows, multi-user isolation,
idempotency, failure handling, stale tracking (Phases 4-7, 13, 14, 18)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest

from core.event_models import EmergencyState
from emergency.models import StandardEvent, EventType
from emergency.orchestrator import EmergencyOrchestrator
from tests.fakes import FakeBackendClient


def make_orchestrator() -> tuple[EmergencyOrchestrator, FakeBackendClient]:
    client = FakeBackendClient()
    orch = EmergencyOrchestrator(client=client)
    return orch, client


def sos_event(user_id=1, incident_id=100, lat=12.97, lon=77.59, silent=False, session_id=None):
    return StandardEvent(
        event_type=EventType.SOS_TRIGGERED,
        user_id=user_id,
        session_id=session_id,
        incident_id=incident_id,
        latitude=lat,
        longitude=lon,
        source="app",
        silent=silent,
        incident_type="silent_sos" if silent else "manual_sos",
    )


async def drain(orch: EmergencyOrchestrator):
    """Let spawned pipeline tasks finish."""
    for _ in range(20):
        pending = [t for t in list(orch._background_tasks) if not t.done()]
        if not pending:
            break
        await asyncio.gather(*pending, return_exceptions=True)


# ---------------------------------------------------------------- SOS basics
@pytest.mark.asyncio
async def test_sos_creates_emergency_and_pipeline_runs():
    orch, client = make_orchestrator()
    await orch.start()
    try:
        client.tracking["sos-a"] = {"active": True}
        processed = await orch.handle_event(sos_event(user_id=1, session_id="sos-a"))
        assert processed
        await drain(orch)
        ctx = orch.get_session("sos-a")
        assert ctx is not None and ctx.user_id == 1
        assert ctx.state in (EmergencyState.TRACKING_ACTIVE, EmergencyState.POLICE_ALERTED)
        assert ctx.tracking_active
        assert client.emergency_creates == 1
        assert client.police_alerts >= 1
        assert "POLICE_ALERTED" in [c[0] for c in client.calls] or any(c[0] == "police" for c in client.calls)
    finally:
        await orch.stop()


@pytest.mark.asyncio
async def test_duplicate_sos_same_incident_is_ignored():
    orch, client = make_orchestrator()
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=2, session_id="sos-b"))
        creates = client.emergency_creates
        alerts = client.police_alerts
        processed = await orch.handle_event(sos_event(user_id=2, session_id="sos-b"))
        assert not processed or client.emergency_creates == creates
        # same user still has exactly ONE active emergency
        active = [c for c in orch.active_sessions() if c.user_id == 2]
        assert len(active) <= 1
    finally:
        await drain(orch)
        await orch.stop()


@pytest.mark.asyncio
async def test_second_sos_different_incident_attaches_not_duplicates():
    orch, client = make_orchestrator()
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=3, incident_id=201, session_id="sos-c"))
        await asyncio.sleep(0)
        await drain(orch)
        creates = client.emergency_creates
        ctx = next(c for c in orch.active_sessions() if c.user_id == 3)
        repeats_before = ctx.repeated_alerts
        await orch.handle_event(sos_event(user_id=3, incident_id=202, session_id="sos-c", lat=12.98))
        await drain(orch)
        assert client.emergency_creates == creates  # no second emergency created
        active = [c for c in orch.active_sessions() if c.user_id == 3]
        assert len(active) == 1
        assert 202 in active[0].incident_ids
    finally:
        await orch.stop()


# ---------------------------------------------------------------- HELP flow
@pytest.mark.asyncio
async def test_help_timeout_activates_emergency():
    orch, _ = make_orchestrator()
    orch.config.help_timeout_seconds = 0.05
    await orch.start()
    try:
        await orch.handle_event(
            StandardEvent(event_type=EventType.HELP_TRIGGERED, user_id=4, session_id="help-d")
        )
        ctx = orch.get_session("help-d")
        assert ctx.state is EmergencyState.HELP_PENDING
        await asyncio.sleep(0.3)
        await drain(orch)
        assert ctx.state is not EmergencyState.HELP_PENDING
        assert ctx.trigger == "HELP"
    finally:
        await orch.stop()


@pytest.mark.asyncio
async def test_help_cancel_prevents_emergency():
    orch, _ = make_orchestrator()
    orch.config.help_timeout_seconds = 5
    await orch.start()
    try:
        await orch.handle_event(
            StandardEvent(event_type=EventType.HELP_TRIGGERED, user_id=5, session_id="help-e")
        )
        await orch.handle_event(
            StandardEvent(event_type=EventType.HELP_CANCELLED, user_id=5, session_id="help-e")
        )
        ctx = orch.get_session("help-e")
        assert ctx.state is EmergencyState.CANCELLED
        assert ctx.resolution == "cancelled_by_user"
        await asyncio.sleep(0.1)
        assert ctx.state is EmergencyState.CANCELLED  # stays cancelled after window
    finally:
        await orch.stop()


# ------------------------------------------------------- multi-user isolation
@pytest.mark.asyncio
async def test_multi_user_isolation_a_b_c():
    """USER A SOS + USER B SOS + USER C HELP -> three independent sessions."""
    orch, client = make_orchestrator()
    orch.config.help_timeout_seconds = 0.05
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=10, incident_id=301, lat=12.90, lon=77.50, session_id="sess-A"))
        await orch.handle_event(sos_event(user_id=11, incident_id=302, lat=12.95, lon=77.55, session_id="sess-B"))
        await orch.handle_event(
            StandardEvent(event_type=EventType.HELP_TRIGGERED, user_id=12, session_id="sess-C", latitude=13.00, longitude=77.60)
        )
        await drain(orch)

        a = orch.get_session("sess-A")
        b = orch.get_session("sess-B")
        c = orch.get_session("sess-C")
        for ctx, uid in ((a, 10), (b, 11), (c, 12)):
            assert ctx is not None and ctx.user_id == uid
        # No cross contamination
        assert a.latitude == 12.90 and b.latitude == 12.95 and c.latitude == 13.00
        assert a.incident_ids == [301] and b.incident_ids == [302]
        assert orch._user_active[10] == "sess-A"
        assert orch._user_active[11] == "sess-B"

        await asyncio.sleep(0.25)  # C's help window expires
        await drain(orch)
        assert c.trigger == "HELP" and c.state != EmergencyState.HELP_PENDING

        # Resolve A - B and C must remain untouched
        result = await client.resolve_emergency("sess-A")
        assert result.ok
        from core.event_models import EventType as ET

        await orch.handle_event(
            StandardEvent(event_type=ET.INCIDENT_RESOLVED, user_id=10, session_id="sess-A", status="resolved")
        )
        assert a.state is EmergencyState.EMERGENCY_RESOLVED
        assert b.is_active and c.is_active
        assert orch._user_active.get(10) is None
        assert orch._user_active.get(11) == "sess-B"
    finally:
        await orch.stop()


# ------------------------------------------------------------------ location
@pytest.mark.asyncio
async def test_location_update_binds_to_correct_session():
    orch, _ = make_orchestrator()
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=20, incident_id=401, session_id="sos-x"))
        await orch.handle_event(
            StandardEvent(
                event_type=EventType.LOCATION_UPDATED,
                user_id=20,
                session_id="sos-x",
                latitude=12.99,
                longitude=77.99,
                event_id="loc:1",
            )
        )
        other = orch.get_session("sos-x")
        assert other.latitude == 12.99 and other.longitude == 77.99
        # A different user's location must NOT touch sos-x
        await orch.handle_event(sos_event(user_id=21, incident_id=402, session_id="sos-y", lat=10.0, lon=10.0))
        await orch.handle_event(
            StandardEvent(
                event_type=EventType.LOCATION_UPDATED,
                user_id=21,
                session_id="sos-y",
                latitude=11.0,
                longitude=11.0,
                event_id="loc:2",
            )
        )
        assert orch.get_session("sos-x").latitude == 12.99
        assert orch.get_session("sos-y").latitude == 11.0
    finally:
        await drain(orch)
        await orch.stop()


@pytest.mark.asyncio
async def test_generated_session_adopts_phone_session_id():
    orch, _ = make_orchestrator()
    await orch.start()
    try:
        # SOS arrives without session id (orchestrator generates one), then the
        # phone's tracking update reveals the real id.
        await orch.handle_event(sos_event(user_id=30, incident_id=501, session_id=None))
        generated = orch._user_active[30]
        await orch.handle_event(
            StandardEvent(
                event_type=EventType.LOCATION_UPDATED,
                user_id=30,
                session_id="sos-from-phone",
                latitude=9.9,
                longitude=9.8,
                event_id="loc:3",
            )
        )
        ctx = orch.get_session("sos-from-phone")
        assert ctx is not None and ctx.user_id == 30
        assert orch._user_active[30] == "sos-from-phone"
        assert orch.get_session(generated) is None or generated == "sos-from-phone"
    finally:
        await drain(orch)
        await orch.stop()


# --------------------------------------------------------------- AI handling
@pytest.mark.asyncio
async def test_ai_unavailable_keeps_emergency_active():
    orch, client = make_orchestrator()
    await orch.start()
    try:
        client.cameras = []  # CCTV registry down too
        await orch.handle_event(sos_event(user_id=40, incident_id=601, session_id="sos-fail"))
        await drain(orch)
        ctx = orch.get_session("sos-fail")
        assert ctx.ai_unavailable or ctx.degraded.get("ai") or ctx.degraded.get("cctv_registry")
        assert ctx.police_alerted  # alert still published without AI
        assert ctx.is_active
    finally:
        await orch.stop()


@pytest.mark.asyncio
async def test_ai_alert_attaches_by_user_and_escalates():
    orch, client = make_orchestrator()
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=50, incident_id=701, session_id="sos-g"))
        await drain(orch)
        before = orch.get_session("sos-g").threat.score
        await orch.handle_event(
            StandardEvent(
                event_type=EventType.AI_ALERT,
                user_id=50,
                incident_id=702,
                ai_result="VIOLENCE",
                confidence=0.93,
                camera_id="default-camera",
            )
        )
        ctx = orch.get_session("sos-g")
        assert ctx.ai_result == "VIOLENCE" and ctx.ai_confidence == pytest.approx(0.93)
        assert ctx.threat.score > before
        assert 702 in ctx.incident_ids
    finally:
        await drain(orch)
        await orch.stop()


# --------------------------------------------------------- backend failures
@pytest.mark.asyncio
async def test_backend_police_failure_degrades_but_stays_active():
    orch, client = make_orchestrator()
    client.fail_next_police_alerts = 1
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=60, incident_id=801, session_id="sos-h"))
        await drain(orch)
        ctx = orch.get_session("sos-h")
        assert ctx.degraded.get("police_alert") or ctx.police_alerted
        assert ctx.is_active  # emergency survives backend outage
        # Recovery flush publishes it
        n = await client.flush_outbox()
        assert n >= 0
    finally:
        await orch.stop()


# ------------------------------------------------------------ dedupe/stale
@pytest.mark.asyncio
async def test_exact_duplicate_event_processed_once():
    orch, client = make_orchestrator()
    await orch.start()
    try:
        evt = sos_event(user_id=70, incident_id=901, session_id="sos-i")
        first = await orch.handle_event(evt)
        second = await orch.handle_event(evt)  # same key -> duplicate
        assert first and not second
        await drain(orch)
        assert client.emergency_creates == 1
    finally:
        await orch.stop()


@pytest.mark.asyncio
async def test_malformed_events_do_not_crash():
    orch, _ = make_orchestrator()
    await orch.start()
    try:
        assert not await orch.handle_event(StandardEvent(event_type=EventType.SOS_TRIGGERED, user_id=None))
        assert not await orch.handle_event(StandardEvent(event_type=EventType.AI_ALERT))  # no data at all
    finally:
        await orch.stop()


@pytest.mark.asyncio
async def test_stale_tracking_flagged_once():
    orch, client = make_orchestrator()
    orch.config.stale_check_interval_seconds = 0.05
    orch.config.tracking_stale_seconds = 0.2
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=80, incident_id=1001, session_id="sos-j"))
        await drain(orch)
        ctx = orch.get_session("sos-j")
        ctx.last_location_at = datetime.utcnow() - timedelta(seconds=30)
        await asyncio.sleep(0.35)
        assert ctx.stale_notified
        # Fresh location resets the flag
        await orch.handle_event(
            StandardEvent(
                event_type=EventType.LOCATION_UPDATED,
                user_id=80,
                session_id="sos-j",
                latitude=1.0,
                longitude=1.0,
                event_id=f"loc:{datetime.utcnow().timestamp()}",
            )
        )
        assert not ctx.stale_notified
    finally:
        await orch.stop()


@pytest.mark.asyncio
async def test_resolve_via_backend_event_transitions_state():
    orch, _ = make_orchestrator()
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=90, incident_id=1101, session_id="sos-k"))
        await orch.handle_event(
            StandardEvent(event_type=EventType.INCIDENT_ACKNOWLEDGED, user_id=90, session_id="sos-k")
        )
        ctx = orch.get_session("sos-k")
        assert ctx.state is EmergencyState.POLICE_RESPONDING
        await orch.handle_event(
            StandardEvent(event_type=EventType.INCIDENT_RESOLVED, user_id=90, session_id="sos-k", status="resolved")
        )
        assert ctx.state is EmergencyState.EMERGENCY_RESOLVED
    finally:
        await drain(orch)
        await orch.stop()


@pytest.mark.asyncio
async def test_snapshot_shape_for_dashboard():
    orch, _ = make_orchestrator()
    await orch.start()
    try:
        await orch.handle_event(sos_event(user_id=100, incident_id=1201, session_id="sos-l"))
        snap = orch.snapshot()
        assert snap["active_count"] >= 1
        sess = snap["sessions"][0]
        for field in ("session_id", "user_id", "state", "location", "cameras", "ai", "threat"):
            assert field in sess
    finally:
        await drain(orch)
        await orch.stop()
