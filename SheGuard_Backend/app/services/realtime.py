import asyncio
from typing import Any
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class RealtimeHub:
    def __init__(self):
        self._connections = set()
        self._session_connections = {}
        self._lock = asyncio.Lock()
        self._loop = None

    def set_loop(self, loop):
        '''Call this from the FastAPI startup event to capture the main loop.'''
        self._loop = loop
        logger.info(f'RealtimeHub.set_loop: Captured main event loop: {loop}')

    def _get_loop(self):
        # Always return the captured loop if we have one - it should be running in the main process
        if self._loop is not None:
            logger.info(f'RealtimeHub._get_loop: returning captured loop={self._loop}, is_running={self._loop.is_running()}')
            return self._loop
        try:
            loop = asyncio.get_running_loop()
            logger.info(f'RealtimeHub._get_loop: got running loop={loop}')
            return loop
        except RuntimeError:
            logger.warning('RealtimeHub._get_loop: no running loop')
            self._loop = None
            return None

    async def connect(self, websocket, session_id=None):
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
            if session_id:
                self._session_connections.setdefault(session_id, set()).add(websocket)
        logger.info(f'RealtimeHub.connect: WS connected. Total connections: {len(self._connections)}, Session connections: {len(self._session_connections.get(session_id, set()))}')

    async def disconnect(self, websocket):
        async with self._lock:
            self._connections.discard(websocket)
            for connections in self._session_connections.values():
                connections.discard(websocket)
        logger.info(f'RealtimeHub.disconnect: WS disconnected. Total connections: {len(self._connections)}')

    async def broadcast(self, event_type, payload):
        message = {'event': event_type, 'payload': payload}
        async with self._lock:
            connections = list(self._connections)
        logger.info(f'RealtimeHub.broadcast: Broadcasting {event_type} to {len(connections)} connections')
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.info(f'RealtimeHub.broadcast: Sent to connection')
            except Exception as e:
                logger.error(f'RealtimeHub.broadcast: Failed to send: {e}')
                await self.disconnect(websocket)

    async def broadcast_session(self, session_id, event_type, payload):
        message = {'event': event_type, 'payload': payload}
        async with self._lock:
            connections = list(self._session_connections.get(session_id, set()))
        logger.info(f'RealtimeHub.broadcast_session: Broadcasting {event_type} to session {session_id} ({len(connections)} connections)')
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.info(f'RealtimeHub.broadcast_session: Sent to session connection')
            except Exception as e:
                logger.error(f'RealtimeHub.broadcast_session: Failed to send: {e}')
                await self.disconnect(websocket)

    def publish_from_sync(self, event_type, payload):
        loop = self._get_loop()
        logger.info(f'RealtimeHub.publish_from_sync: {event_type}, loop={loop}, running={loop.is_running() if loop else None}')
        if loop and loop.is_running():
            logger.info('RealtimeHub.publish_from_sync: Scheduling broadcast task via run_coroutine_threadsafe')
            asyncio.run_coroutine_threadsafe(self.broadcast(event_type, payload), loop)
        else:
            logger.warning('RealtimeHub.publish_from_sync: No running loop, cannot publish')

    def publish_session_from_sync(self, session_id, event_type, payload):
        loop = self._get_loop()
        logger.info(f'RealtimeHub.publish_session_from_sync: {event_type} for session {session_id}, loop={loop}, running={loop.is_running() if loop else None}')
        if loop and loop.is_running():
            logger.info('RealtimeHub.publish_session_from_sync: Scheduling session broadcast task via run_coroutine_threadsafe')
            asyncio.run_coroutine_threadsafe(self.broadcast_session(session_id, event_type, payload), loop)
        else:
            logger.warning('RealtimeHub.publish_session_from_sync: No running loop, cannot publish session')


realtime_hub = RealtimeHub()
