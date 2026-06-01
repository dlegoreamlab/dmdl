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
        subtitle_langs: Optional[List[str] | str] = None,
        subtitle_format: str = "best",
        format_selector: Optional[str] = None,
        merge_output_format: str = "mp4",
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
        self.subtitle_langs = subtitle_langs if subtitle_langs is not None else ["ko", "en"]
        self.subtitle_format = subtitle_format
        self.format_selector = format_selector
        self.merge_output_format = merge_output_format
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
            "subtitle_langs": self.subtitle_langs,
            "subtitle_format": self.subtitle_format,
            "format_selector": self.format_selector,
            "merge_output_format": self.merge_output_format,
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
        quality: Optional[str] = None,
        subtitle: Optional[bool] = None,
        subtitle_langs: Optional[List[str] | str] = None,
        subtitle_format: Optional[str] = None,
        format_selector: Optional[str] = None,
        merge_output_format: Optional[str] = None,
        thumbnail: Optional[bool] = None,
        playlist: Optional[bool] = None,
    ) -> DownloadResult:
        merged_options = dict(options or {})
        if quality is not None:
            merged_options["quality"] = quality
        if subtitle is not None:
            merged_options["subtitle"] = subtitle
        if subtitle_langs is not None:
            merged_options["subtitle_langs"] = subtitle_langs
        if subtitle_format is not None:
            merged_options["subtitle_format"] = subtitle_format
        if format_selector is not None:
            merged_options["format_selector"] = format_selector
        if merge_output_format is not None:
            merged_options["merge_output_format"] = merge_output_format
        if thumbnail is not None:
            merged_options["thumbnail"] = thumbnail
        if playlist is not None:
            merged_options["playlist"] = playlist

        task = self._build_task(
            url=url,
            requested_type=requested_type,
            output_dir=output_dir,
            adapter_hint=adapter_hint,
            options=merged_options,
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
                "subtitle_langs": item.get(
                    "subtitle_langs",
                    item_options.get("subtitle_langs", self.subtitle_langs),
                ),
                "subtitle_format": item.get(
                    "subtitle_format",
                    item_options.get("subtitle_format", self.subtitle_format),
                ),
                "format_selector": item.get(
                    "format_selector",
                    item_options.get("format_selector", self.format_selector),
                ),
                "merge_output_format": item.get(
                    "merge_output_format",
                    item_options.get("merge_output_format", self.merge_output_format),
                ),
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
