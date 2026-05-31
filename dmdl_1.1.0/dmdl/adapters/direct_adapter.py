from __future__ import annotations

import asyncio
import mimetypes
import shutil
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ..models.download_task import DownloadTask
from ..utils.filename import guess_filename_from_headers, guess_filename_from_url
from ..utils.path import build_output_path


class DirectAdapter:
    name = "direct"
    _DEFAULT_HEADERS = {"User-Agent": "dmdl/1.0"}

    def can_handle(self, task: DownloadTask) -> bool:
        parsed = urlparse(task.url)
        return parsed.scheme in {"http", "https"}

    async def download(self, task: DownloadTask) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._download_sync, task)

    def _download_sync(self, task: DownloadTask) -> Dict[str, Any]:
        timeout = int(task.options.get("timeout", 60))
        chunk_size = int(task.options.get("chunk_size", 1024 * 1024))
        headers = {**self._DEFAULT_HEADERS, **dict(task.options.get("headers", {}))}

        req = Request(task.url, headers=headers)
        with urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get_content_type()
            content_length = response.headers.get("Content-Length")
            content_disposition = response.headers.get("Content-Disposition")

            fallback_name = guess_filename_from_url(task.url)
            filename = guess_filename_from_headers(content_disposition, fallback=fallback_name)
            if "." not in Path(filename).name:
                ext = mimetypes.guess_extension(content_type or "") or ""
                filename = f"{filename}{ext}"

            output_path = build_output_path(task.output_dir, filename)
            with Path(output_path).open("wb") as handle:
                shutil.copyfileobj(response, handle, length=chunk_size)

        file_size = Path(output_path).stat().st_size
        return {
            "saved_path": str(output_path),
            "metadata": {
                "source_url": task.url,
                "title": Path(output_path).name,
                "content_type": content_type,
                "content_length_header": int(content_length) if content_length and content_length.isdigit() else None,
                "size": file_size,
                "filename": Path(output_path).name,
                "extension": Path(output_path).suffix.lower(),
            },
        }
