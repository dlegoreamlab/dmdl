from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

import yt_dlp

from ..models.download_task import DownloadTask
from ..utils.path import ensure_dir


class YtDlpAdapter:
    name = "ytdlp"
    SUPPORTED_PLATFORM_DOMAINS = {
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "vimeo.com": "vimeo",
        "instagram.com": "instagram",
        "instagr.am": "instagram",
    }

    def can_handle(self, task: DownloadTask) -> bool:
        hostname = (urlparse(task.url).hostname or "").lower()
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in self.SUPPORTED_PLATFORM_DOMAINS
        )

    async def download(self, task: DownloadTask) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._download_sync, task)

    def _download_sync(self, task: DownloadTask) -> Dict[str, Any]:
        out_dir = ensure_dir(task.output_dir)
        quality = task.options.get("quality", "best")
        subtitle = bool(task.options.get("subtitle", True))
        subtitle_langs = self._normalize_subtitle_langs(task.options.get("subtitle_langs", ["ko", "en"]))
        subtitle_format = str(task.options.get("subtitle_format", "best"))
        format_selector = task.options.get("format_selector")
        thumbnail = bool(task.options.get("thumbnail", True))
        playlist = bool(task.options.get("playlist", False))
        timeout = int(task.options.get("timeout", 60))
        merge_output_format = str(task.options.get("merge_output_format", "mp4"))

        opts: Dict[str, Any] = {
            "outtmpl": str(out_dir / "%(title)s [%(id)s].%(ext)s"),
            "format": self._resolve_format_selector(quality, format_selector),
            "noplaylist": not playlist,
            "writethumbnail": thumbnail,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": timeout,
            "merge_output_format": merge_output_format,
        }
        if subtitle:
            opts.update(
                {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": subtitle_langs,
                    "subtitlesformat": subtitle_format,
                }
            )

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(task.url, download=True)
            entries: List[Dict[str, Any]] = list(self._iter_entries(info))
            primary = entries[0]
            saved_path = ydl.prepare_filename(primary)
            prepared_path = Path(saved_path)
            if prepared_path.suffix.lower() != f".{merge_output_format.lower()}":
                merged_candidate = prepared_path.with_suffix(f".{merge_output_format.lower()}")
                if merged_candidate.exists():
                    saved_path = str(merged_candidate)
                else:
                    mp4_candidate = prepared_path.with_suffix(".mp4")
                    if mp4_candidate.exists():
                        saved_path = str(mp4_candidate)

        saved_file = Path(saved_path)
        video_size = saved_file.stat().st_size if saved_file.exists() else None
        source_platform = self._detect_platform(task.url, primary)
        subtitle_path = self._find_related_file(saved_file, {".vtt", ".srt", ".ass"})
        thumbnail_path = self._find_related_file(saved_file, {".jpg", ".jpeg", ".png", ".webp"})

        metadata: Dict[str, Any] = {
            "video_id": primary.get("id"),
            "title": primary.get("title"),
            "channel_id": primary.get("channel_id") or primary.get("uploader_id"),
            "channel_title": primary.get("uploader") or primary.get("channel") or primary.get("creator"),
            "published_at": primary.get("upload_date") or primary.get("release_date") or primary.get("timestamp"),
            "duration": primary.get("duration"),
            "view_count": primary.get("view_count"),
            "like_count": primary.get("like_count"),
            "comment_count": primary.get("comment_count"),
            "category_id": primary.get("category"),
            "default_language": primary.get("language"),
            "thumbnail_url": primary.get("thumbnail"),
            "description": primary.get("description"),
            "tags": primary.get("tags"),
            "downloaded": True,
            "audio_path": None,
            "subtitle_path": str(subtitle_path) if subtitle_path else None,
            "video_size": video_size,
            "audio_size": None,
            "width": primary.get("width"),
            "height": primary.get("height"),
            "fps": primary.get("fps"),
            "codec": primary.get("vcodec"),
            "size": video_size,
            "source_type": "yt_dlp",
            "source_platform": source_platform,
            "extractor": primary.get("extractor_key") or primary.get("extractor"),
            "webpage_url": primary.get("webpage_url") or task.url,
            "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
            "playlist_count": len(entries) if len(entries) > 1 else None,
            "requested_quality": str(quality),
            "requested_subtitle_langs": subtitle_langs if subtitle else [],
            "requested_subtitle_format": subtitle_format if subtitle else None,
        }

        return {
            "saved_path": str(saved_file),
            "metadata": metadata,
        }

    def _iter_entries(self, info: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        entries = info.get("entries")
        if isinstance(entries, list) and entries:
            for entry in entries:
                if entry:
                    yield entry
            return
        yield info

    def _find_related_file(self, saved_file: Path, extensions: set[str]) -> Path | None:
        parent = saved_file.parent
        stem = saved_file.stem
        exact_candidates = [parent / f"{stem}{ext}" for ext in extensions]
        for candidate in exact_candidates:
            if candidate.exists():
                return candidate

        prefix = f"{stem}."
        for child in parent.iterdir():
            if child.is_file() and child.name.startswith(prefix) and child.suffix.lower() in extensions:
                return child
        return None

    def _detect_platform(self, url: str, info: Dict[str, Any]) -> str:
        extractor = (info.get("extractor_key") or info.get("extractor") or "").lower()
        if "instagram" in extractor:
            return "instagram"
        if "youtube" in extractor:
            return "youtube"
        if "vimeo" in extractor:
            return "vimeo"

        hostname = (urlparse(url).hostname or "").lower()
        for domain, platform in self.SUPPORTED_PLATFORM_DOMAINS.items():
            if hostname == domain or hostname.endswith(f".{domain}"):
                return platform
        return "unknown"

    def _normalize_subtitle_langs(self, subtitle_langs: Any) -> List[str]:
        if isinstance(subtitle_langs, str):
            items = [item.strip() for item in subtitle_langs.split(",") if item.strip()]
            return items or ["ko", "en"]
        if isinstance(subtitle_langs, (list, tuple, set)):
            items = [str(item).strip() for item in subtitle_langs if str(item).strip()]
            return items or ["ko", "en"]
        return ["ko", "en"]

    def _resolve_format_selector(self, quality: Any, format_selector: Any) -> str:
        if format_selector:
            return str(format_selector)

        quality_text = str(quality).strip().lower()
        quality_aliases = {
            "best": "bestvideo+bestaudio/best",
            "source": "bestvideo+bestaudio/best",
            "worst": "worstvideo+worstaudio/worst",
            "audio": "bestaudio/best",
            "audio_only": "bestaudio/best",
        }
        if quality_text in quality_aliases:
            return quality_aliases[quality_text]

        numeric = "".join(ch for ch in quality_text if ch.isdigit())
        if numeric:
            return f"bestvideo[height<={int(numeric)}]+bestaudio/best[height<={int(numeric)}]/best"

        return str(quality)
