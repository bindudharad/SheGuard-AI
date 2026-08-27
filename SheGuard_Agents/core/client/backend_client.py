"""Backend API client for SheGuard Agents.

Async HTTP client with retry, a circuit breaker, idempotent publishes and an
offline outbox so the orchestrator survives backend downtime. All endpoints
match the existing SheGuard_Backend routes (root prefix - no /api/v1).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from emergency.config import EmergencyConfig, get_emergency_config

logger = logging.getLogger("sheguard.agents.backend")

SOS_INCIDENT_TYPES = {"manual_sos", "silent_sos", "sos", "help"}


@dataclass
class ClientResult:
    ok: bool
    status: int = 0
    data: Any = None
    error: Optional[str] = None


@dataclass
class _CircuitBreaker:
    threshold: int = 4
    cooldown_seconds: float = 15.0
    failures: int = 0
    opened_at: Optional[float] = None

    @property
    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.monotonic() - self.opened_at >= self.cooldown_seconds:
            self.opened_at = None
            self.failures = 0
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = time.monotonic()
            logger.warning("[AGENT] Backend circuit breaker OPEN for %.1fs", self.cooldown_seconds)


class BackendClient:
    """All communication with SheGuard_Backend happens through this class."""

    def __init__(self, config: Optional[EmergencyConfig] = None) -> None:
        self.config = config or get_emergency_config()
        self._client: Optional[httpx.AsyncClient] = None
        self._breaker = _CircuitBreaker(self.config.circuit_breaker_threshold, self.config.circuit_breaker_cooldown_seconds)
        self._user_token: Optional[str] = None
        self._token_user_id: Optional[int] = None
        self._login_lock = asyncio.Lock()
        # Outbox for publishes that fail while the backend is down.
        self._outbox: List[Dict[str, Any]] = []
        self._outbox_lock = asyncio.Lock()
        # Idempotency guard for side-effectful publishes.
        self._publish_keys: Dict[str, float] = {}

    # ------------------------------------------------------------------ core
    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.config.request_timeout_seconds)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
        auth: bool = True,
        use_service_token: bool = False,
        retry: bool = True,
    ) -> ClientResult:
        if self._client is None:
            await self.start()
        assert self._client is not None

        if self._breaker.is_open:
            return ClientResult(ok=False, error="circuit breaker open (backend unreachable)")

        headers: Dict[str, str] = {}
        if auth:
            token: Optional[str] = None
            if use_service_token and self.config.service_token:
                token = self.config.service_token
            else:
                token = await self._ensure_user_token() if auth else None
            if token:
                headers["Authorization"] = f"Bearer {token}"

        attempts = self.config.max_retries if retry else 1
        delay = self.config.retry_base_delay_seconds
        last_error: Optional[str] = None
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.request(
                    method,
                    self.config.backend_url + path,
                    json=json_body,
                    params=params,
                    headers=headers or None,
                )
                if response.status_code in (401, 403) and auth and not use_service_token:
                    # Token expired/invalid - refresh once and retry immediately.
                    self._user_token = None
                    token = await self._ensure_user_token()
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                    response = await self._client.request(
                        method,
                        self.config.backend_url + path,
                        json=json_body,
                        params=params,
                        headers=headers or None,
                    )
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError(f"server {response.status_code}", request=response.request, response=response)
                self._breaker.record_success()
                if response.status_code >= 400:
                    return ClientResult(ok=False, status=response.status_code, error=response.text[:300])
                try:
                    return ClientResult(ok=True, status=response.status_code, data=response.json())
                except ValueError:
                    return ClientResult(ok=True, status=response.status_code, data=None)
            except (httpx.TransportError, httpx.HTTPStatusError, asyncio.TimeoutError) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < attempts:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, self.config.retry_base_delay_seconds * 8)
        self._breaker.record_failure()
        return ClientResult(ok=False, error=last_error or "request failed")

    # ------------------------------------------------------------------ auth
    async def _ensure_user_token(self) -> Optional[str]:
        async with self._login_lock:
            if self._user_token:
                return self._user_token
            if not self.config.agent_phone_number or not self.config.agent_password:
                return None
            try:
                response = await self._client.post(  # type: ignore[union-attr]
                    self.config.backend_url + "/login",
                    json={"phone_number": self.config.agent_phone_number, "password": self.config.agent_password},
                )
                if response.status_code == 200:
                    data = response.json()
                    self._user_token = data.get("access_token")
                    self._token_user_id = data.get("user_id")
                    logger.info("[AGENT] Service login OK (user_id=%s)", self._token_user_id)
                    return self._user_token
                logger.error("[AGENT] Service login failed: %s %s", response.status_code, response.text[:200])
            except Exception as exc:  # noqa: BLE001 - never crash on auth
                logger.error("[AGENT] Service login error: %s", exc)
            return None

    # ----------------------------------------------------------------- reads
    async def health(self) -> ClientResult:
        return await self._request("GET", "/", auth=False)

    async def get_live_location(self, user_id: int) -> ClientResult:
        return await self._request("GET", f"/location/live/{user_id}", auth=False)

    async def get_tracking_live(self, session_id: str) -> ClientResult:
        return await self._request("GET", f"/tracking/live/{session_id}", auth=False)

    async def list_cameras(self) -> ClientResult:
        result = await self._request("GET", "/camera/list")
        if not result.ok and self.config.service_token:
            # /agents/cameras accepts the shared service token explicitly.
            result = await self._request("GET", "/agents/cameras", use_service_token=True)
        return result

    async def agent_live_snapshot(self) -> ClientResult:
        return await self._request("GET", "/agents/live", use_service_token=True or bool(self.config.service_token))

    # --------------------------------------------------------------- writes
    def _seen_recently(self, key: str, ttl: float) -> bool:
        """True => this side effect was already confirmed recently (skip)."""
        now = time.monotonic()
        self._publish_keys = {k: ts for k, ts in self._publish_keys.items() if now - ts < ttl}
        return key in self._publish_keys

    def _mark_seen(self, key: str) -> None:
        self._publish_keys[key] = time.monotonic()

    async def create_emergency_session(
        self,
        user_id: int,
        session_id: str,
        incident_id: Optional[int],
        latitude: Optional[float],
        longitude: Optional[float],
        trigger_source: str,
        idempotency_key: Optional[str] = None,
    ) -> ClientResult:
        key = f"emergency:{idempotency_key}" if idempotency_key else None
        if key and self._seen_recently(key, self.config.idempotency_ttl_seconds):
            return ClientResult(ok=True, data={"duplicate": True})
        body = {
            "user_id": user_id,
            "session_id": session_id,
            "incident_id": incident_id,
            "latitude": latitude,
            "longitude": longitude,
            "trigger_source": trigger_source,
        }
        return await self._enqueue_or_send("POST", "/agents/emergency/start", body, idempotency_key=key)

    async def push_agent_state(self, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> ClientResult:
        key = f"state:{idempotency_key}" if idempotency_key else None
        if key and self._seen_recently(key, 120):
            return ClientResult(ok=True, data={"duplicate": True})
        return await self._enqueue_or_send("POST", "/agents/state", payload, idempotency_key=key)

    async def police_alert(self, payload: Dict[str, Any], idempotency_key: Optional[str] = None) -> ClientResult:
        key = f"police:{idempotency_key}" if idempotency_key else None
        if key and self._seen_recently(key, self.config.idempotency_ttl_seconds):
            return ClientResult(ok=True, data={"duplicate": True})
        return await self._enqueue_or_send("POST", "/agents/police-alert", payload, idempotency_key=key)

    async def resolve_emergency(self, session_id: str) -> ClientResult:
        return await self._request("POST", f"/emergency/session/{session_id}/resolve")

    async def acknowledge_emergency(self, session_id: str) -> ClientResult:
        return await self._request("POST", f"/emergency/session/{session_id}/acknowledge")

    # ------------------------------------------------------------ outbox
    async def _enqueue_or_send(self, method: str, path: str, body: dict, idempotency_key: Optional[str]) -> ClientResult:
        result = await self._request(method, path, json_body=body, use_service_token=True)
        if result.ok:
            if idempotency_key:
                self._mark_seen(idempotency_key)
            return result
        if idempotency_key and "circuit breaker" not in (result.error or ""):
            # Definite failure worth retrying later. Breaker-open failures are
            # also queued by the caller via flush cycles.
            await self._queue_outbox(method, path, body, idempotency_key)
        elif idempotency_key:
            await self._queue_outbox(method, path, body, idempotency_key)
        return result

    async def _queue_outbox(self, method: str, path: str, body: dict, key: str) -> None:
        async with self._outbox_lock:
            if any(item["key"] == key for item in self._outbox):
                return
            self._outbox.append({"method": method, "path": path, "body": body, "key": key})
            logger.warning("[AGENT] Queued %s %s (backend unavailable, outbox=%d)", method, path, len(self._outbox))

    async def flush_outbox(self) -> int:
        """Retry queued publishes; returns number flushed."""
        async with self._outbox_lock:
            items = list(self._outbox)
            self._outbox.clear()
        flushed = 0
        for item in items:
            if self._seen_recently(item["key"], self.config.idempotency_ttl_seconds):
                flushed += 1  # already succeeded before queueing
                continue
            result = await self._request(item["method"], item["path"], json_body=item["body"], use_service_token=True)
            if result.ok:
                self._mark_seen(item["key"])
                flushed += 1
            else:
                await self._queue_outbox(item["method"], item["path"], item["body"], item["key"])
        return flushed

    @property
    def outbox_size(self) -> int:
        return len(self._outbox)

    @property
    def breaker_open(self) -> bool:
        return self._breaker.is_open
