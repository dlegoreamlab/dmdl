from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from ..models.download_task import DownloadTask


@runtime_checkable
class AdapterProtocol(Protocol):
    name: str

    def can_handle(self, task: DownloadTask) -> bool: ...

    async def download(self, task: DownloadTask) -> dict[str, Any]: ...


def validate_adapter(adapter: object) -> AdapterProtocol:
    for attr in ("name", "can_handle", "download"):
        if not hasattr(adapter, attr):
            raise TypeError(f"Adapter must implement '{attr}'.")
    return adapter  # type: ignore[return-value]
