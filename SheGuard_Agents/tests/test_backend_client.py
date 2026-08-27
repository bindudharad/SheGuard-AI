"""BackendClient resilience tests: retry, breaker behaviour via faked transport,
idempotency keys and outbox queueing (Phase 13/14/16)."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from core.client.backend_client import BackendClient
from emergency.config import EmergencyConfig


def make_config(**overrides) -> EmergencyConfig:
    defaults = dict(
        backend_url="http://backend-test:59999",  # nothing listens here
        service_token="test-token",
        agent_phone_number="",  # skip login
        request_timeout_seconds=0.2,
        max_retries=2,
        retry_base_delay_seconds=0.01,
        circuit_breaker_threshold=2,
        circuit_breaker_cooldown_seconds=0.1,
        help_timeout_seconds=5.0,
        tracking_stale_seconds=60.0,
        stale_check_interval_seconds=10.0,
        duplicate_sos_window_seconds=30.0,
        idempotency_ttl_seconds=3600.0,
    )
    defaults.update(overrides)
    return EmergencyConfig(**defaults)


@pytest.mark.asyncio
async def test_unreachable_backend_returns_failure_not_exception():
    client = BackendClient(make_config())
    await client.start()
    try:
        result = await client.push_agent_state({"session_id": "s", "state": "TRACKING_ACTIVE"})
        assert not result.ok
        assert result.error
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_failed_publish_is_queued_and_flushed_when_backend_down():
    client = BackendClient(make_config())
    await client.start()
    try:
        result = await client.police_alert({"session_id": "s", "threat_level": "HIGH"}, idempotency_key="s:HIGH")
        assert not result.ok
        assert client.outbox_size == 1
        flushed = await client.flush_outbox()  # still down -> stays queued
        assert flushed == 0
        assert client.outbox_size == 1
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_repeated_failures():
    client = BackendClient(make_config(circuit_breaker_threshold=1))
    await client.start()
    try:
        first = await client.health()
        assert not first.ok
        second = await client.health()
        assert not second.ok and "circuit breaker" in (second.error or "")
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_idempotency_key_blocks_duplicate_side_effect(monkeypatch):
    client = BackendClient(make_config())
    await client.start()
    calls = {"n": 0}

    async def fake_request(*args, **kwargs):
        calls["n"] += 1
        from core.client.backend_client import ClientResult

        return ClientResult(ok=True)

    monkeypatch.setattr(client, "_request", fake_request)
    try:
        await client.create_emergency_session(1, "sess-1", None, None, None, "manual_sos", idempotency_key="sess-1")
        await client.create_emergency_session(1, "sess-1", None, None, None, "manual_sos", idempotency_key="sess-1")
        assert calls["n"] == 1  # second call short-circuited
    finally:
        await client.stop()
