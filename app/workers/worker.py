import asyncio
import logging
from typing import Callable, Coroutine

logger = logging.getLogger(__name__)


class JobQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()

    async def enqueue(self, job) -> None:
        await self._queue.put(job)
        logger.info("Enqueued job %s", getattr(job, "id", "unknown"))

    async def work(self, handler: Callable[[object], Coroutine]) -> None:
        while True:
            job = await self._queue.get()
            try:
                await handler(job)
            finally:
                self._queue.task_done()
