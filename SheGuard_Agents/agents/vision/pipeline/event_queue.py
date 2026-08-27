"""
Async backend event queue with background worker.
Prevents blocking the camera/inference loop with HTTP requests.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from collections import deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority levels for events - critical incidents have higher priority"""
    LOW = 0      # Telemetry, routine updates
    NORMAL = 1   # Standard incidents
    HIGH = 2     # Suspicious behaviors, following
    CRITICAL = 3 # Emergency, immediate threats


@dataclass
class QueuedEvent:
    """Event waiting to be sent to backend"""
    event_type: str
    payload: Dict[str, Any]
    priority: EventPriority = EventPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    retries: int = 0
    max_retries: int = 3
    timeout_seconds: float = 10.0
    callback: Optional[Callable] = None
    
    def __lt__(self, other):
        # Higher priority first, then older first
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value
        return self.created_at < other.created_at


class BackendEventQueue:
    """
    Thread-safe async queue for backend events.
    Runs a background worker that processes events without blocking the inference loop.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        worker_count: int = 2,
        send_func: Optional[Callable] = None,
    ):
        self.max_size = max_size
        self.worker_count = worker_count
        self.send_func = send_func
        
        # Priority queue (using asyncio.PriorityQueue)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue(maxsize=max_size)
        
        # Metrics
        self._metrics = {
            'enqueued': 0,
            'sent': 0,
            'failed': 0,
            'dropped_low_priority': 0,
            'retries': 0,
            'queue_overflow': 0,
        }
        self._metrics_lock = asyncio.Lock()
        
        # Workers
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._shutdown_event = asyncio.Event()
        
    async def start(self):
        """Start background workers"""
        if self._running:
            return
        self._running = True
        self._shutdown_event.clear()
        
        for i in range(self.worker_count):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)
        
        logger.info(f"[BackendEventQueue] Started {self.worker_count} workers")
    
    async def stop(self, timeout: float = 5.0):
        """Graceful shutdown - wait for queue to drain"""
        self._running = False
        self._shutdown_event.set()
        
        # Wait for workers to finish
        if self._workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._workers, return_exceptions=True),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning("[BackendEventQueue] Workers did not finish in time")
        
        # Process remaining items synchronously
        await self._drain_queue()
        logger.info("[BackendEventQueue] Stopped")
    
    async def enqueue(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: EventPriority = EventPriority.NORMAL,
        callback: Optional[Callable] = None,
        max_retries: int = 3,
        timeout_seconds: float = 10.0,
    ) -> bool:
        """
        Add event to queue. Returns False if queue is full and event is LOW priority.
        Critical events will wait for space.
        """
        event = QueuedEvent(
            event_type=event_type,
            payload=payload,
            priority=priority,
            callback=callback,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
        )
        
        try:
            # Critical events wait for space, low priority events get dropped
            if priority == EventPriority.LOW:
                self._queue.put_nowait(event)
            else:
                await asyncio.wait_for(self._queue.put(event), timeout=1.0)
            
            async with self._metrics_lock:
                self._metrics['enqueued'] += 1
            return True
            
        except asyncio.QueueFull:
            async with self._metrics_lock:
                if priority == EventPriority.LOW:
                    self._metrics['dropped_low_priority'] += 1
                    logger.warning(f"[BackendEventQueue] Dropped LOW priority event: {event_type}")
                else:
                    self._metrics['queue_overflow'] += 1
                    logger.error(f"[BackendEventQueue] Queue full, could not enqueue {priority.name}: {event_type}")
            return False
    
    async def _worker_loop(self, worker_id: int):
        """Background worker that processes queued events"""
        logger.info(f"[BackendEventQueue] Worker {worker_id} started")
        
        while self._running or not self._queue.empty():
            try:
                # Wait for event with timeout to check shutdown
                event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                
                await self._process_event(event, worker_id)
                self._queue.task_done()
                
            except asyncio.TimeoutError:
                # Check if we should continue
                if not self._running and self._queue.empty():
                    break
                continue
            except Exception as e:
                logger.error(f"[BackendEventQueue] Worker {worker_id} error: {e}")
        
        logger.info(f"[BackendEventQueue] Worker {worker_id} stopped")
    
    async def _process_event(self, event: QueuedEvent, worker_id: int):
        """Process a single event with retries"""
        if not self.send_func:
            logger.warning("[BackendEventQueue] No send function configured")
            return
        
        last_error = None
        
        for attempt in range(event.max_retries + 1):
            if not self._running and attempt > 0:
                # Don't retry on shutdown unless it's the first attempt
                break
            
            try:
                # Apply timeout to the send operation
                await asyncio.wait_for(
                    self.send_func(event.event_type, event.payload),
                    timeout=event.timeout_seconds
                )
                
                async with self._metrics_lock:
                    self._metrics['sent'] += 1
                
                # Call success callback if provided
                if event.callback:
                    try:
                        await event.callback(True, None)
                    except Exception as e:
                        logger.error(f"[BackendEventQueue] Callback error: {e}")
                
                return  # Success
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {event.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)
            
            async with self._metrics_lock:
                self._metrics['retries'] += 1
            
            if attempt < event.max_retries:
                # Exponential backoff: 0.5s, 1s, 2s
                backoff = 0.5 * (2 ** attempt)
                logger.warning(f"[BackendEventQueue] Retry {attempt + 1}/{event.max_retries} for {event.event_type}: {last_error}")
                await asyncio.sleep(backoff)
        
        # All retries failed
        async with self._metrics_lock:
            self._metrics['failed'] += 1
        
        logger.error(f"[BackendEventQueue] Failed to send {event.event_type} after {event.max_retries} retries: {last_error}")
        
        # Call failure callback if provided
        if event.callback:
            try:
                await event.callback(False, last_error)
            except Exception as e:
                logger.error(f"[BackendEventQueue] Failure callback error: {e}")
    
    async def _drain_queue(self):
        """Process remaining events synchronously on shutdown"""
        while not self._queue.empty():
            try:
                event = self._queue.get_nowait()
                await self._process_event(event, -1)
            except Exception as e:
                logger.error(f"[BackendEventQueue] Drain error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current queue metrics"""
        return {
            **self._metrics,
            'queue_size': self._queue.qsize(),
            'queue_max_size': self.max_size,
            'running': self._running,
        }
    
    def get_queue_size(self) -> int:
        return self._queue.qsize()


# Global instance (initialized in VisionAgent)
_event_queue: Optional[BackendEventQueue] = None


def get_event_queue() -> Optional[BackendEventQueue]:
    return _event_queue


def set_event_queue(queue: BackendEventQueue):
    global _event_queue
    _event_queue = queue
