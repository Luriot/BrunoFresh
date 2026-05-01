import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import AsyncGenerator


@dataclass
class JobEvent:
    status: str
    message: str | None = None
    extra: dict | None = None


class JobEventBus:
    def __init__(self) -> None:
        self._listeners: dict[int, set[asyncio.Queue[JobEvent]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def publish(self, job_id: int, event: JobEvent) -> None:
        async with self._lock:
            listeners = list(self._listeners.get(job_id, set()))

        for queue in listeners:
            await queue.put(event)

    async def subscribe(self, job_id: int) -> AsyncGenerator[asyncio.Queue[JobEvent], None]:
        queue: asyncio.Queue[JobEvent] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._listeners[job_id].add(queue)

        try:
            yield queue
        finally:
            async with self._lock:
                listeners = self._listeners.get(job_id)
                if listeners is not None:
                    listeners.discard(queue)
                    if not listeners:
                        self._listeners.pop(job_id, None)


job_event_bus = JobEventBus()
