from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..models.download_task import DownloadTask


@dataclass(order=True)
class PrioritizedTask:
    priority: int
    sequence: int
    task: DownloadTask = field(compare=False)


class DownloadQueue:
    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[PrioritizedTask] = asyncio.PriorityQueue()
        self._sequence = 0

    async def put(self, task: DownloadTask) -> None:
        self._sequence += 1
        await self._queue.put(PrioritizedTask(task.priority, self._sequence, task))

    async def get(self) -> DownloadTask:
        item = await self._queue.get()
        return item.task

    def task_done(self) -> None:
        self._queue.task_done()

    async def join(self) -> None:
        await self._queue.join()
