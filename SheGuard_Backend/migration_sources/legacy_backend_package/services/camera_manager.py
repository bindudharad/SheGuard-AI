from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import cv2


@dataclass
class CameraHealth:
    camera_id: str
    source: str
    online: bool = False
    fps: float = 0.0
    latency_ms: float = 0.0
    last_frame_at: float | None = None
    reconnects: int = 0
    error: str | None = None


@dataclass
class CameraSource:
    camera_id: str
    source: str | int
    name: str | None = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class CameraManager:
    def __init__(self) -> None:
        self.sources: dict[str, CameraSource] = {}
        self.health: dict[str, CameraHealth] = {}
        self._threads: list[threading.Thread] = []
        self._stop = threading.Event()

    def add_camera(self, source: CameraSource) -> None:
        self.sources[source.camera_id] = source
        self.health[source.camera_id] = CameraHealth(source.camera_id, str(source.source))

    def start_all(self, frame_handler: Callable[[str, Any], None]) -> None:
        self._stop.clear()
        for source in self.sources.values():
            if not source.enabled:
                continue
            thread = threading.Thread(target=self._run_camera, args=(source, frame_handler), daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop_all(self) -> None:
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=2.0)
        self._threads.clear()

    def status(self) -> list[dict[str, Any]]:
        return [health.__dict__.copy() for health in self.health.values()]

    def _run_camera(self, source: CameraSource, frame_handler: Callable[[str, Any], None]) -> None:
        health = self.health[source.camera_id]
        while not self._stop.is_set():
            cap = cv2.VideoCapture(source.source)
            if not cap.isOpened():
                health.online = False
                health.error = "connection_failed"
                health.reconnects += 1
                time.sleep(2.0)
                continue
            health.online = True
            last_tick = time.time()
            while not self._stop.is_set():
                started = time.time()
                ok, frame = cap.read()
                if not ok:
                    health.online = False
                    health.error = "frame_read_failed"
                    health.reconnects += 1
                    break
                frame_handler(source.camera_id, frame)
                now = time.time()
                health.last_frame_at = now
                health.latency_ms = (now - started) * 1000
                health.fps = 1.0 / max(now - last_tick, 1e-6)
                health.error = None
                last_tick = now
            cap.release()
            time.sleep(1.0)

