from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import uuid


class AgentStatus(str, Enum):
    OFFLINE = "OFFLINE"
    INITIALIZING = "INITIALIZING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    ERROR = "ERROR"
    DEGRADED = "DEGRADED"
    STOPPED = "STOPPED"


@dataclass
class AgentHealth:
    name: str
    version: str
    status: AgentStatus
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    events_processed: int = 0
    errors: int = 0
    avg_latency_ms: float = 0.0
    component_status: Dict[str, str] = field(default_factory=dict)
    current_task: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "events_processed": self.events_processed,
            "errors": self.errors,
            "avg_latency_ms": self.avg_latency_ms,
            "component_status": self.component_status,
            "current_task": self.current_task,
            "details": self.details,
        }


@dataclass
class AgentMessage:
    event_id: str
    timestamp: datetime
    agent: str
    event_type: str
    incident_id: Optional[str] = None
    trace_id: Optional[str] = None
    confidence: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        agent: str,
        event_type: str,
        data: Dict[str, Any],
        incident_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        confidence: float = 0.0,
    ) -> "AgentMessage":
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            agent=agent,
            event_type=event_type,
            incident_id=incident_id,
            trace_id=trace_id or str(uuid.uuid4()),
            confidence=confidence,
            data=data,
        )


class BaseAgent:
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self._status = AgentStatus.OFFLINE
        self._health = AgentHealth(name=name, version=version, status=AgentStatus.OFFLINE)
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._start_time: Optional[datetime] = None

    @property
    def status(self) -> AgentStatus:
        return self._status

    @property
    def health(self) -> AgentHealth:
        return self._health

    async def initialize(self) -> None:
        self._set_status(AgentStatus.INITIALIZING)
        await self._initialize()
        self._set_status(AgentStatus.READY)

    async def _initialize(self) -> None:
        raise NotImplementedError

    async def process(self, message: AgentMessage) -> Optional[AgentMessage]:
        if self._status not in (AgentStatus.READY, AgentStatus.RUNNING):
            raise RuntimeError(f"Agent {self.name} not ready: {self._status}")
        self._set_status(AgentStatus.RUNNING)
        start = datetime.utcnow()
        try:
            result = await self._process(message)
            latency = (datetime.utcnow() - start).total_seconds() * 1000
            self._update_latency(latency)
            self._health.events_processed += 1
            return result
        except Exception as e:
            self._health.errors += 1
            self._set_status(AgentStatus.ERROR)
            raise
        finally:
            if self._status == AgentStatus.RUNNING:
                self._set_status(AgentStatus.READY)

    async def _process(self, message: AgentMessage) -> Optional[AgentMessage]:
        raise NotImplementedError

    async def health(self) -> AgentHealth:
        self._health.last_heartbeat = datetime.utcnow()
        return self._health

    async def shutdown(self) -> None:
        self._set_status(AgentStatus.STOPPED)
        await self._shutdown()

    async def _shutdown(self) -> None:
        pass

    def _set_status(self, status: AgentStatus) -> None:
        self._status = status
        self._health.status = status

    def _update_latency(self, latency_ms: float) -> None:
        n = self._health.events_processed
        if n > 0:
            self._health.avg_latency_ms = (
                (self._health.avg_latency_ms * n + latency_ms) / (n + 1)
            )
        else:
            self._health.avg_latency_ms = latency_ms
