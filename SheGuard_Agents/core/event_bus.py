from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import inspect
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


class EventBus:
    """Async publish/subscribe event bus with a module-level singleton."""

    _default_instance: Optional["EventBus"] = None

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def default(cls) -> "EventBus":
        if cls._default_instance is None:
            cls._default_instance = EventBus()
        return cls._default_instance

    @classmethod
    async def subscribe(cls, event_type: str) -> asyncio.Queue:
        return await cls.default()._subscribe(event_type)

    @classmethod
    async def unsubscribe(cls, event_type: str, queue: asyncio.Queue) -> None:
        await cls.default()._unsubscribe(event_type, queue)

    @classmethod
    async def publish(cls, message: "AgentMessage") -> None:
        await cls.default()._publish(message)

    @classmethod
    async def publish_event(
        cls,
        event_type: str,
        data: Dict[str, Any],
        agent: str,
        incident_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        confidence: float = 0.0,
    ) -> None:
        await cls.default()._publish_event(event_type, data, agent, incident_id, trace_id, confidence)

    async def _subscribe(self, event_type: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(queue)
        return queue

    async def _unsubscribe(self, event_type: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(queue)
                if not self._subscribers[event_type]:
                    del self._subscribers[event_type]

    async def _publish(self, message: AgentMessage) -> None:
        async with self._lock:
            queues = self._subscribers.get(message.event_type, []).copy()
        for queue in queues:
            try:
                await queue.put(message)
            except Exception:
                pass

    async def _publish_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        agent: str,
        incident_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        confidence: float = 0.0,
    ) -> None:
        message = AgentMessage.create(agent, event_type, data, incident_id, trace_id, confidence)
        await self._publish(message)


# Module-level singleton for convenience
event_bus = EventBus.default()


class AgentRegistry:
    """Registry of active agents keyed by name."""

    _default_instance: Optional["AgentRegistry"] = None

    def __init__(self):
        self._agents: Dict[str, "BaseAgent"] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def default(cls) -> "AgentRegistry":
        if cls._default_instance is None:
            cls._default_instance = AgentRegistry()
        return cls._default_instance

    async def register(self, agent: "BaseAgent") -> None:
        async with self._lock:
            self._agents[agent.name] = agent

    async def unregister(self, name: str) -> None:
        async with self._lock:
            self._agents.pop(name, None)

    async def get(self, name: str) -> Optional["BaseAgent"]:
        async with self._lock:
            return self._agents.get(name)

    async def list_agents(self) -> List[Dict[str, Any]]:
        async with self._lock:
            results = []
            for agent in self._agents.values():
                h = agent.health
                if asyncio.iscoroutinefunction(type(h)):
                    h = await h()
                elif inspect.iscoroutinefunction(getattr(agent, "health", None)):
                    h = await agent.health()
                results.append(h.to_dict())
            return results

    async def get_health(self, name: str) -> Optional[AgentHealth]:
        agent = await self.get(name)
        if agent:
            return await agent.health()
        return None
