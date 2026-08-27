from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._session_connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: str | None = None) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            if session_id:
                self._session_connections.setdefault(session_id, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)
            for connections in self._session_connections.values():
                connections.discard(websocket)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        message = {"event": event_type, "payload": payload}
        async with self._lock:
            connections = list(self._connections)
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)

    async def broadcast_session(self, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
        message = {"event": event_type, "payload": payload}
        async with self._lock:
            connections = list(self._session_connections.get(session_id, set()))
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.disconnect(websocket)

    def publish_from_sync(self, event_type: str, payload: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.broadcast(event_type, payload))

    def publish_session_from_sync(self, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self.broadcast_session(session_id, event_type, payload))


realtime_hub = RealtimeHub()
