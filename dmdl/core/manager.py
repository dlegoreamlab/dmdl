from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from ..logging import LoggerProtocol, get_logger
from ..models.download_result import DownloadResult
from ..models.download_task import DownloadTask
from ..plugins import AdapterRegistry
from .metadata import MetadataManager


class DownloadManager:
    def __init__(
        self,
        node_id: str = "local",
        *,
        registry: AdapterRegistry | None = None,
        logger: LoggerProtocol | None = None,
        auto_load_plugins: bool = True,
        plugin_entrypoint_group: str = "dmdl.adapters",
    ) -> None:
        self.logger = logger or get_logger("dmdl.manager")
        self.metadata = MetadataManager(node_id=node_id)
        self.registry = registry or AdapterRegistry(logger=self.logger)
        if not self.registry.adapters:
            self.registry.load_builtin(replace=True)
        if auto_load_plugins:
            self.load_plugins_from_entrypoints(group=plugin_entrypoint_group)

    @property
    def adapters(self):
        return self.registry.adapters

    @adapters.setter
    def adapters(self, adapters: List[object]) -> None:
        self.registry.set_adapters(adapters)

    def register_adapter(self, adapter: object) -> None:
        self.registry.register(adapter, prepend=True)

    def load_plugins_from_entrypoints(self, group: str = "dmdl.adapters") -> None:
        try:
            loaded = self.registry.load_entrypoints(group=group, prepend=True)
            if loaded:
                self.logger.info(
                    "plugin adapters loaded",
                    group=group,
                    adapters=[adapter.name for adapter in loaded],
                )
        except Exception as exc:
            self.logger.warning(
                "plugin discovery skipped",
                group=group,
                error=str(exc),
            )

    def load_plugins(self, import_paths: List[str]) -> None:
        loaded = self.registry.load_import_paths(import_paths, prepend=True)
        self.logger.info(
            "plugin adapters loaded from import paths",
            adapters=[adapter.name for adapter in loaded],
        )

    def pick_adapter(self, task: DownloadTask):
        adapter = self.registry.pick(task)
        self.logger.debug(
            "adapter selected",
            task_id=task.task_id,
            adapter=adapter.name,
            adapter_hint=task.adapter_hint,
            source_url=task.url,
        )
        return adapter

    async def run_task(self, task: DownloadTask) -> DownloadResult:
        self.logger.event(
            "download_started",
            task_id=task.task_id,
            source_url=task.url,
            requested_type=task.requested_type,
            output_dir=task.output_dir,
        )
        adapter = self.pick_adapter(task)
        try:
            payload = await adapter.download(task)
            saved_path = payload.get("saved_path")
            metadata = payload.get("metadata", {})
            record_type = task.requested_type or self._infer_type(saved_path=saved_path, adapter=adapter, metadata=metadata)
            record = self.metadata.build_record(
                source_url=task.url,
                path=saved_path,
                record_type=record_type,
                meta=metadata,
            )
            result = DownloadResult(
                task_id=task.task_id,
                success=True,
                source_url=task.url,
                adapter=getattr(adapter, "name", adapter.__class__.__name__),
                record=record,
                saved_path=saved_path,
                metadata=metadata,
            )
            self.logger.event(
                "download_completed",
                task_id=task.task_id,
                adapter=result.adapter,
                saved_path=saved_path,
                record_id=record.id,
            )
            return result
        except Exception as exc:
            self.logger.error(
                "download failed",
                task_id=task.task_id,
                adapter=getattr(adapter, "name", adapter.__class__.__name__),
                source_url=task.url,
                error=str(exc),
            )
            return DownloadResult(
                task_id=task.task_id,
                success=False,
                source_url=task.url,
                adapter=getattr(adapter, "name", adapter.__class__.__name__),
                error=str(exc),
            )

    async def run_many(self, tasks: List[DownloadTask], *, concurrency: int = 3) -> List[DownloadResult]:
        if not tasks:
            return []

        limit = max(1, int(concurrency))
        semaphore = asyncio.Semaphore(limit)
        self.logger.info("batch download queued", total=len(tasks), concurrency=limit)

        async def _runner(task: DownloadTask) -> DownloadResult:
            async with semaphore:
                return await self.run_task(task)

        results = list(await asyncio.gather(*(_runner(task) for task in tasks)))
        success_count = sum(1 for item in results if item.success)
        self.logger.info(
            "batch download finished",
            total=len(results),
            success=success_count,
            failed=len(results) - success_count,
        )
        return results

    def _infer_type(self, *, saved_path: str | None, adapter: object, metadata: dict) -> str:
        adapter_name = getattr(adapter, "name", "")
        if metadata.get("detected_record_type"):
            return str(metadata["detected_record_type"])
        if adapter_name == "ytdlp":
            if (metadata.get("source_platform") or "").lower() == "youtube":
                return "youtube_video"
            return "video"

        content_type = (metadata.get("content_type") or "").lower()
        suffix = Path(saved_path or "").suffix.lower()
        if "pdf" in content_type or suffix == ".pdf":
            return "pdf"
        if content_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            return "image"
        if content_type.startswith("video/") or suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
            return "video"
        if content_type.startswith("audio/") or suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
            return "music"
        return "article"
