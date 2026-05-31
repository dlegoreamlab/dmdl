from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse

from ..models.download_task import DownloadTask
from .direct_adapter import DirectAdapter


class GenericAdapter:
    name = "generic"

    def __init__(self) -> None:
        self._direct = DirectAdapter()

    def can_handle(self, task: DownloadTask) -> bool:
        parsed = urlparse(task.url)
        return parsed.scheme in {"http", "https"}

    async def download(self, task: DownloadTask) -> Dict[str, Any]:
        return await self._direct.download(task)
