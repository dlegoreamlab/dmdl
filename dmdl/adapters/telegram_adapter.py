from __future__ import annotations

import asyncio
import json
import mimetypes
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, TypeVar
from urllib.parse import urlparse

from telethon import TelegramClient
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession
from telethon.tl.functions.messages import ImportChatInviteRequest

from ..models.download_task import DownloadTask
from ..utils.filename import sanitize_filename
from ..utils.path import build_output_path, ensure_dir

T = TypeVar("T")


class TelegramAdapter:
    name = "telegram"
    SUPPORTED_HOSTS = {
        "t.me",
        "www.t.me",
        "telegram.me",
        "www.telegram.me",
    }

    def can_handle(self, task: DownloadTask) -> bool:
        hostname = (urlparse(task.url).hostname or "").lower()
        return hostname in self.SUPPORTED_HOSTS

    async def download(self, task: DownloadTask) -> Dict[str, Any]:
        cfg = self._resolve_config(task)
        client = self._build_client(cfg)
        await client.connect()
        try:
            await self._ensure_authorized(client, cfg)
            entity, source_meta = await self._resolve_entity(client, task, cfg)
            messages = await self._collect_messages(client, entity, task, cfg)
            if not messages:
                raise ValueError("다운로드 가능한 텔레그램 미디어 메시지를 찾지 못했습니다.")

            downloads = await self._download_messages(client, messages, task, cfg, source_meta)
            if not downloads:
                raise ValueError("선택한 메시지들에 미디어가 없거나 저장에 실패했습니다.")

            manifest_path = self._write_manifest(task, source_meta, downloads)
            primary = downloads[0]
            metadata = self._build_result_metadata(task, source_meta, downloads, manifest_path)
            saved_path = str(primary["saved_path"]) if len(downloads) == 1 else str(manifest_path)
            return {
                "saved_path": saved_path,
                "metadata": metadata,
            }
        finally:
            await client.disconnect()

    def _resolve_config(self, task: DownloadTask) -> Dict[str, Any]:
        options = dict(task.options or {})
        nested = dict(options.get("telegram", {}))
        flat: Dict[str, Any] = {
            key: value for key, value in options.items() if str(key).startswith("telegram_")
        }

        cfg: Dict[str, Any] = {**nested, **flat}
        cfg.setdefault("api_id", cfg.get("telegram_api_id") or os.getenv("DMDL_TELEGRAM_API_ID"))
        cfg.setdefault("api_hash", cfg.get("telegram_api_hash") or os.getenv("DMDL_TELEGRAM_API_HASH"))
        cfg.setdefault(
            "session",
            cfg.get("telegram_session") or os.getenv("DMDL_TELEGRAM_SESSION") or "dmdl_telegram",
        )
        cfg.setdefault(
            "session_string",
            cfg.get("telegram_session_string") or os.getenv("DMDL_TELEGRAM_SESSION_STRING"),
        )
        cfg.setdefault("bot_token", cfg.get("telegram_bot_token") or os.getenv("DMDL_TELEGRAM_BOT_TOKEN"))
        cfg.setdefault("chat", cfg.get("telegram_chat"))
        cfg.setdefault("message_ids", cfg.get("telegram_message_ids"))
        cfg.setdefault("from_message_id", cfg.get("telegram_from_message_id"))
        cfg.setdefault("to_message_id", cfg.get("telegram_to_message_id"))
        cfg.setdefault("limit", int(cfg.get("telegram_limit", 1)))
        cfg.setdefault("batch_size", int(cfg.get("telegram_batch_size", 50)))
        cfg.setdefault("max_flood_wait", int(cfg.get("telegram_max_flood_wait", 300)))
        cfg.setdefault("wait_buffer", int(cfg.get("telegram_wait_buffer", 3)))
        cfg.setdefault("retry_limit", int(cfg.get("telegram_retry_limit", 5)))
        cfg.setdefault("per_file_delay", float(cfg.get("telegram_per_file_delay", 0.0)))
        cfg.setdefault(
            "join_via_invite",
            bool(cfg.get("telegram_join_via_invite", False)),
        )
        cfg.setdefault(
            "range_limit",
            int(cfg.get("telegram_range_limit", 200)),
        )

        if not cfg.get("api_id") or not cfg.get("api_hash"):
            raise ValueError(
                "텔레그램 API 자격증명이 없습니다. options.telegram_api_id / telegram_api_hash 또는 DMDL_TELEGRAM_API_ID / DMDL_TELEGRAM_API_HASH 환경변수를 설정하세요."
            )
        return cfg

    def _build_client(self, cfg: Dict[str, Any]) -> TelegramClient:
        session_value = cfg.get("session")
        session_string = cfg.get("session_string")
        session_obj = StringSession(session_string) if session_string else session_value
        return TelegramClient(
            session_obj,
            int(cfg["api_id"]),
            str(cfg["api_hash"]),
            request_retries=0,
            connection_retries=1,
            auto_reconnect=False,
        )

    async def _ensure_authorized(self, client: TelegramClient, cfg: Dict[str, Any]) -> None:
        bot_token = cfg.get("bot_token")
        if bot_token:
            await self._call_with_floodwait(lambda: client.start(bot_token=bot_token), cfg)
            return

        if await client.is_user_authorized():
            return

        raise ValueError(
            "텔레그램 세션이 인증되지 않았습니다. 먼저 Telethon 세션 문자열(session string) 또는 로그인된 세션 파일을 준비하세요."
        )

    async def _resolve_entity(self, client: TelegramClient, task: DownloadTask, cfg: Dict[str, Any]):
        parsed = urlparse(task.url)
        parts = [part for part in parsed.path.split("/") if part]

        chat_ref = cfg.get("chat")
        if not chat_ref and parts:
            if parts[0] == "c" and len(parts) >= 2 and parts[1].isdigit():
                chat_ref = int(f"-100{parts[1]}")
            elif parts[0].startswith("+"):
                invite_hash = parts[0][1:]
                if not cfg.get("join_via_invite"):
                    raise ValueError(
                        "초대 링크(+hash)로 직접 접근하려면 telegram_join_via_invite=true 를 명시해야 합니다. 기본값은 비활성화입니다."
                    )
                result = await self._call_with_floodwait(
                    lambda: client(ImportChatInviteRequest(invite_hash)),
                    cfg,
                )
                if not getattr(result, "chats", None):
                    raise ValueError("초대 링크에서 채팅 정보를 확인하지 못했습니다.")
                entity = result.chats[0]
                return entity, self._build_source_meta(entity, task.url)
            elif parts[0] != "joinchat":
                chat_ref = parts[0]

        if not chat_ref:
            raise ValueError(
                "대상 채팅을 해석할 수 없습니다. t.me/<username>/<msg_id>, t.me/c/<internal_id>/<msg_id> 형식을 사용하거나 telegram_chat 옵션을 지정하세요."
            )

        entity = await self._call_with_floodwait(lambda: client.get_entity(chat_ref), cfg)
        return entity, self._build_source_meta(entity, task.url)

    async def _collect_messages(self, client: TelegramClient, entity: Any, task: DownloadTask, cfg: Dict[str, Any]):
        message_ids = self._resolve_message_ids(task, cfg)
        if message_ids:
            return await self._fetch_messages_by_ids(client, entity, message_ids, cfg)

        limit = max(1, int(cfg.get("limit", 1)))
        probe_limit = max(limit * 5, limit)
        recent = await self._call_with_floodwait(
            lambda: client.get_messages(entity, limit=probe_limit),
            cfg,
        )
        collected = [message for message in recent if message and getattr(message, "media", None)]
        return collected[:limit]

    def _resolve_message_ids(self, task: DownloadTask, cfg: Dict[str, Any]) -> list[int]:
        parsed = urlparse(task.url)
        parts = [part for part in parsed.path.split("/") if part]

        raw_ids = cfg.get("message_ids")
        ids: list[int] = []
        if isinstance(raw_ids, int):
            ids.append(raw_ids)
        elif isinstance(raw_ids, Iterable) and not isinstance(raw_ids, (str, bytes, dict)):
            ids.extend(int(item) for item in raw_ids)
        elif isinstance(raw_ids, str) and raw_ids.strip():
            ids.extend(int(item.strip()) for item in raw_ids.split(",") if item.strip())

        if parts and parts[-1].isdigit():
            ids.append(int(parts[-1]))

        from_message_id = cfg.get("from_message_id")
        to_message_id = cfg.get("to_message_id")
        if from_message_id is not None and to_message_id is not None:
            start = int(from_message_id)
            end = int(to_message_id)
            if end < start:
                start, end = end, start
            count = end - start + 1
            if count > int(cfg.get("range_limit", 200)):
                raise ValueError(
                    f"요청 범위가 너무 큽니다 ({count}개). telegram_range_limit 이하로 줄이세요."
                )
            ids.extend(range(start, end + 1))

        seen: set[int] = set()
        normalized: list[int] = []
        for item in ids:
            if item <= 0 or item in seen:
                continue
            seen.add(item)
            normalized.append(item)
        return normalized

    async def _fetch_messages_by_ids(self, client: TelegramClient, entity: Any, message_ids: list[int], cfg: Dict[str, Any]):
        batch_size = max(1, int(cfg.get("batch_size", 50)))
        collected = []
        for index in range(0, len(message_ids), batch_size):
            batch = message_ids[index:index + batch_size]
            result = await self._call_with_floodwait(
                lambda current=batch: client.get_messages(entity, ids=current),
                cfg,
            )
            if isinstance(result, list):
                collected.extend(item for item in result if item)
            elif result:
                collected.append(result)
        return [message for message in collected if getattr(message, "media", None)]

    async def _download_messages(
        self,
        client: TelegramClient,
        messages: list[Any],
        task: DownloadTask,
        cfg: Dict[str, Any],
        source_meta: Dict[str, Any],
    ) -> list[Dict[str, Any]]:
        chat_dir = ensure_dir(Path(task.output_dir) / sanitize_filename(source_meta["chat_title"]))
        saved: list[Dict[str, Any]] = []
        per_file_delay = max(0.0, float(cfg.get("per_file_delay", 0.0)))

        for message in messages:
            if not getattr(message, "media", None):
                continue

            target_path = build_output_path(chat_dir, self._build_filename(message))
            saved_path = await self._call_with_floodwait(
                lambda current_message=message, current_target=target_path: client.download_media(
                    current_message,
                    file=str(current_target),
                ),
                cfg,
            )
            if not saved_path:
                continue

            file_path = Path(saved_path)
            file_info = getattr(message, "file", None)
            mime_type = getattr(file_info, "mime_type", None)
            record_type = self._infer_record_type(mime_type, file_path)
            saved.append(
                {
                    "message_id": int(message.id),
                    "saved_path": str(file_path),
                    "filename": file_path.name,
                    "size": file_path.stat().st_size if file_path.exists() else None,
                    "content_type": mime_type,
                    "duration": getattr(file_info, "duration", None),
                    "width": getattr(file_info, "width", None),
                    "height": getattr(file_info, "height", None),
                    "record_type": record_type,
                    "caption": getattr(message, "message", None),
                }
            )
            if per_file_delay > 0:
                await asyncio.sleep(per_file_delay)
        return saved

    def _write_manifest(self, task: DownloadTask, source_meta: Dict[str, Any], downloads: list[Dict[str, Any]]) -> Path:
        manifest_dir = ensure_dir(task.output_dir)
        manifest_name = sanitize_filename(
            f"telegram_manifest_{source_meta['chat_id']}_{downloads[0]['message_id']}_{downloads[-1]['message_id']}.json"
        )
        manifest_path = build_output_path(manifest_dir, manifest_name)
        payload = {
            "source": source_meta,
            "downloads": downloads,
        }
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_path

    def _build_result_metadata(
        self,
        task: DownloadTask,
        source_meta: Dict[str, Any],
        downloads: list[Dict[str, Any]],
        manifest_path: Path,
    ) -> Dict[str, Any]:
        primary = downloads[0]
        return {
            "title": primary["filename"] if len(downloads) == 1 else source_meta["chat_title"],
            "source_url": task.url,
            "content_type": primary.get("content_type"),
            "duration": primary.get("duration"),
            "width": primary.get("width"),
            "height": primary.get("height"),
            "size": primary.get("size"),
            "source_type": "telegram",
            "detected_record_type": primary.get("record_type") or "article",
            "download_count": len(downloads),
            "manifest_path": str(manifest_path),
            "telegram_chat_id": source_meta.get("chat_id"),
            "telegram_chat_title": source_meta.get("chat_title"),
            "telegram_message_ids": [item["message_id"] for item in downloads],
        }

    def _build_source_meta(self, entity: Any, source_url: str) -> Dict[str, Any]:
        title = (
            getattr(entity, "title", None)
            or getattr(entity, "username", None)
            or f"chat_{getattr(entity, 'id', 'unknown')}"
        )
        return {
            "source_url": source_url,
            "chat_id": getattr(entity, "id", "unknown"),
            "chat_title": sanitize_filename(str(title)),
        }

    def _build_filename(self, message: Any) -> str:
        file_info = getattr(message, "file", None)
        mime_type = getattr(file_info, "mime_type", None) or "application/octet-stream"
        original_name = getattr(file_info, "name", None)
        ext = getattr(file_info, "ext", None) or mimetypes.guess_extension(mime_type) or ""
        if original_name:
            return sanitize_filename(original_name)
        date_prefix = message.date.strftime("%Y%m%d_%H%M%S") if getattr(message, "date", None) else "telegram"
        return sanitize_filename(f"{date_prefix}_{message.id}{ext}")

    def _infer_record_type(self, mime_type: str | None, path: Path) -> str:
        content_type = (mime_type or "").lower()
        suffix = path.suffix.lower()
        if content_type.startswith("video/") or suffix in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
            return "video"
        if content_type.startswith("audio/") or suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
            return "music"
        if content_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            return "image"
        if content_type == "application/pdf" or suffix == ".pdf":
            return "pdf"
        return "article"

    async def _call_with_floodwait(
        self,
        func: Callable[[], Awaitable[T]],
        cfg: Dict[str, Any],
    ) -> T:
        retry_limit = max(0, int(cfg.get("retry_limit", 5)))
        max_flood_wait = max(0, int(cfg.get("max_flood_wait", 300)))
        wait_buffer = max(0, int(cfg.get("wait_buffer", 3)))
        attempt = 0

        while True:
            try:
                return await func()
            except FloodWaitError as exc:
                attempt += 1
                wait_seconds = int(getattr(exc, "seconds", 0)) + wait_buffer
                if attempt > retry_limit or wait_seconds > max_flood_wait:
                    raise ValueError(
                        f"FloodWait {wait_seconds}초가 필요해 중단했습니다. telegram_max_flood_wait 값을 높이거나 요청량을 줄이세요."
                    ) from exc
                await asyncio.sleep(wait_seconds)
            except SessionPasswordNeededError as exc:
                raise ValueError(
                    "2단계 인증이 필요한 계정입니다. 미리 인증된 session string 또는 세션 파일을 사용하세요."
                ) from exc
