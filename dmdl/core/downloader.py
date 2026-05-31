from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..logging import LoggerProtocol
from ..models.download_result import DownloadResult
from ..models.download_task import DownloadTask
from ..plugins import AdapterRegistry
from .manager import DownloadManager


class Downloader:
    def __init__(
        self,
        quality: str = "1080p",
        subtitle: bool = True,
        thumbnail: bool = True,
        playlist: bool = False,
        download_dir: str = "downloads",
        node_id: str = "local",
        max_concurrency: int = 3,
        logger: LoggerProtocol | None = None,
        registry: AdapterRegistry | None = None,
        auto_load_plugins: bool = True,
    ):
        self.quality = quality
        self.subtitle = subtitle
        self.thumbnail = thumbnail
        self.playlist = playlist
        self.download_dir = download_dir
        self.max_concurrency = max(1, int(max_concurrency))
        self.manager = DownloadManager(
            node_id=node_id,
            registry=registry,
            logger=logger,
            auto_load_plugins=auto_load_plugins,
        )

    def register_adapter(self, adapter: object) -> None:
        self.manager.register_adapter(adapter)

    def load_plugins(self, import_paths: List[str]) -> None:
        self.manager.load_plugins(import_paths)

    def _default_options(self) -> Dict[str, Any]:
        return {
            "quality": self.quality,
            "subtitle": self.subtitle,
            "thumbnail": self.thumbnail,
            "playlist": self.playlist,
        }

    def _build_task(
        self,
        *,
        url: str,
        requested_type: Optional[str] = None,
        output_dir: Optional[str] = None,
        adapter_hint: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 100,
    ) -> DownloadTask:
        return DownloadTask(
            url=url,
            requested_type=requested_type,
            output_dir=output_dir or self.download_dir,
            adapter_hint=adapter_hint,
            options={**self._default_options(), **(options or {})},
            context=context or {},
            priority=priority,
        )

    async def download(
        self,
        url: str,
        requested_type: Optional[str] = None,
        output_dir: Optional[str] = None,
        adapter_hint: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 100,
    ) -> DownloadResult:
        task = self._build_task(
            url=url,
            requested_type=requested_type,
            output_dir=output_dir,
            adapter_hint=adapter_hint,
            options=options,
            context=context,
            priority=priority,
        )
        return await self.manager.run_task(task)

    async def download_many(self, targets: List[Dict[str, Any]]) -> List[DownloadResult]:
        tasks: List[DownloadTask] = []

        for item in targets:
            url = item.get("url")
            if not url:
                raise ValueError("Each target must include a non-empty 'url'.")

            item_options = dict(item.get("options", {}))
            merged_options = {
                **self._default_options(),
                **item_options,
                "quality": item.get("quality", item_options.get("quality", self.quality)),
                "subtitle": item.get("subtitle", item_options.get("subtitle", self.subtitle)),
                "thumbnail": item.get("thumbnail", item_options.get("thumbnail", self.thumbnail)),
                "playlist": item.get("playlist", item_options.get("playlist", self.playlist)),
            }

            tasks.append(
                self._build_task(
                    url=url,
                    requested_type=item.get("requested_type"),
                    output_dir=item.get("output_dir", self.download_dir),
                    adapter_hint=item.get("adapter_hint"),
                    options=merged_options,
                    context=item.get("context", {}),
                    priority=item.get("priority", 100),
                )
            )

        return await self.manager.run_many(tasks, concurrency=self.max_concurrency)
