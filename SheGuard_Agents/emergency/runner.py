"""Composes the emergency orchestrator with its backend connections.

Used by api/main.py (embedded in the agents API process) and by scripts/e2e_demo.py.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from core.client.backend_client import BackendClient
from emergency.ai_client import AICoordinator
from emergency.config import EmergencyConfig, get_emergency_config
from emergency.orchestrator import EmergencyOrchestrator
from emergency.ws_client import LiveEventClient

logger = logging.getLogger("sheguard.agents.runner")


class EmergencyRunner:
    def __init__(self, config: Optional[EmergencyConfig] = None) -> None:
        self.config = config or get_emergency_config()
        self.client = BackendClient(self.config)
        self.ai = AICoordinator(self.config)
        self.orchestrator = EmergencyOrchestrator(client=self.client, ai=self.ai, config=self.config)
        self.ws = LiveEventClient(handler=self.orchestrator.handle_event, config=self.config)
        self._started = False

    def start_background(self) -> None:
        """Start from a context without a running loop (FastAPI startup has one,
        but this also supports plain script usage)."""
        try:
            loop = _get_or_create_loop()
            loop.run_until_complete(self.start())
        except RuntimeError:
            threading.Thread(target=lambda: _get_or_create_loop().run_until_complete(self.start()), daemon=True).start()

    async def start(self) -> None:
        if self._started:
            return
        await self.orchestrator.start()
        self.ws.start()
        self._started = True
        logger.info("[AGENT] EmergencyRunner started (backend=%s)", self.config.backend_url)

    async def stop(self) -> None:
        if not self._started:
            return
        await self.ws.stop()
        await self.orchestrator.stop()
        self._started = False


_loops: dict = {}


def _get_or_create_loop():
    import asyncio

    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        pass
    thread_id = threading.get_ident()
    loop = _loops.get(thread_id)
    if loop is None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _loops[thread_id] = loop
    return loop


_runner: Optional[EmergencyRunner] = None


def get_runner() -> EmergencyRunner:
    global _runner
    if _runner is None:
        _runner = EmergencyRunner()
    return _runner
