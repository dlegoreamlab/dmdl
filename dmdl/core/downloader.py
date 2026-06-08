from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from ..logging import LoggerProtocol
from ..models.download_result import DownloadResult
from ..models.download_task import DownloadTask
from ..plugins import AdapterRegistry
from .manager import DownloadManager

# DICL→DMDL bridge: map DFSS FileRecord.type → DMDL requested_type.
# DMDL valid types: article, image, music, pdf, video, youtube_video.
_DICL_RECORD_TYPE_MAP: Dict[str, str] = {
    "image": "image",
    "video": "video",
    "audio": "music",   # DMDL has no "audio" type; closest match is music.
    "music": "music",
    "pdf": "pdf",
}


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

    # ------------------------------------------------------------------
    # DICL bridge
    # ------------------------------------------------------------------
    async def download_from_file_record(
        self,
        file_record: Any,
        *,
        output_dir: Optional[str] = None,
        adapter_hint: Optional[str] = "telegram",
        options: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 100,
    ) -> DownloadResult:
        """Download the media referenced by a DICL telegram FileRecord.

        ``file_record`` may be either a DFSS ``FileRecord`` instance or a
        plain ``dict`` with the same shape (``path``, ``type``, ``meta``).

        The bridge:
          * Uses ``record.path`` as the task URL (supports both
            ``https://t.me/<username>/<id>`` and
            ``telegram://chat/<chat_id>/message/<id>``).
          * Forwards ``record.meta.relation`` into ``task.context
            ['dicl_relation']`` so :class:`TelegramAdapter` can recover the
            chat / message id even when they are not encoded in the URL.
          * Maps the DFSS record ``type`` to a DMDL ``requested_type``
            (``audio`` is folded into ``music`` because DMDL has no
            dedicated audio type).
        """
        task_kwargs = self._task_kwargs_from_file_record(
            file_record,
            output_dir=output_dir,
            adapter_hint=adapter_hint,
            options=options,
            context=context,
            priority=priority,
        )
        return await self.download(**task_kwargs)

    async def download_from_file_records(
        self,
        file_records: Iterable[Any],
        *,
        output_dir: Optional[str] = None,
        adapter_hint: Optional[str] = "telegram",
        options: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 100,
    ) -> List[DownloadResult]:
        """Batch variant of :meth:`download_from_file_record`.

        Internally builds one DMDL target per record and dispatches them
        through :meth:`download_many`, so the configured ``max_concurrency``
        is honoured.
        """
        targets: List[Dict[str, Any]] = []
        for record in file_records:
            kwargs = self._task_kwargs_from_file_record(
                record,
                output_dir=output_dir,
                adapter_hint=adapter_hint,
                options=options,
                context=context,
                priority=priority,
            )
            targets.append(
                {
                    "url": kwargs["url"],
                    "requested_type": kwargs.get("requested_type"),
                    "output_dir": kwargs.get("output_dir") or self.download_dir,
                    "adapter_hint": kwargs.get("adapter_hint"),
                    "options": kwargs.get("options", {}),
                    "context": kwargs.get("context", {}),
                    "priority": kwargs.get("priority", priority),
                }
            )
        return await self.download_many(targets)

    @staticmethod
    def _task_kwargs_from_file_record(
        file_record: Any,
        *,
        output_dir: Optional[str],
        adapter_hint: Optional[str],
        options: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
        priority: int,
    ) -> Dict[str, Any]:
        path, record_type, meta = _extract_file_record_fields(file_record)
        if not path:
            raise ValueError("FileRecord.path is required to start a download.")

        relation = dict((meta.get("relation") or {}))
        fields = dict((meta.get("fields") or {}))

        merged_context: Dict[str, Any] = dict(context or {})
        if relation:
            merged_context.setdefault("dicl_relation", relation)
        merged_context.setdefault("dicl_record_type", record_type)
        if fields.get("file_name"):
            merged_context.setdefault("dicl_file_name", fields["file_name"])

        requested_type = _DICL_RECORD_TYPE_MAP.get((record_type or "").lower())

        return {
            "url": path,
            "requested_type": requested_type,
            "output_dir": output_dir,
            "adapter_hint": adapter_hint,
            "options": dict(options or {}),
            "context": merged_context,
            "priority": priority,
        }

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


def _extract_file_record_fields(file_record: Any) -> tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """Read ``path``, ``type`` and ``meta`` from either a DFSS FileRecord
    object or a plain dict that mirrors its shape.

    Kept tolerant on purpose so DICL callers can hand us either form.
    """
    if file_record is None:
        return None, None, {}

    if isinstance(file_record, dict):
        path = file_record.get("path")
        record_type = file_record.get("type")
        meta = file_record.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        return path, record_type, meta

    path = getattr(file_record, "path", None)
    record_type = getattr(file_record, "type", None)
    meta = getattr(file_record, "meta", None) or {}
    if not isinstance(meta, dict):
        # Some FileRecord implementations expose meta as a dataclass / mapping
        # proxy; fall back to to_dict() if available.
        to_dict = getattr(file_record, "to_dict", None)
        if callable(to_dict):
            try:
                dumped = to_dict()
                if isinstance(dumped, dict):
                    meta = dumped.get("meta") or {}
                    path = path or dumped.get("path")
                    record_type = record_type or dumped.get("type")
            except Exception:
                meta = {}
        else:
            meta = {}
    return path, record_type, meta
