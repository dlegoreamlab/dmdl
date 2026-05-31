from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


_INVALID_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')


def sanitize_filename(name: str, replacement: str = "_") -> str:
    cleaned = _INVALID_CHARS.sub(replacement, str(name)).strip(" .")
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    return cleaned or "download"


def guess_filename_from_url(url: str, fallback: str = "download") -> str:
    parsed = urlparse(url)
    candidate = Path(unquote(parsed.path)).name or fallback
    return sanitize_filename(candidate)


def guess_filename_from_headers(content_disposition: str | None, fallback: str = "download") -> str:
    if not content_disposition:
        return sanitize_filename(fallback)

    parts = [part.strip() for part in content_disposition.split(";")]
    for part in parts:
        if part.lower().startswith("filename*="):
            value = part.split("=", 1)[1]
            if "''" in value:
                _, encoded = value.split("''", 1)
                return sanitize_filename(unquote(encoded.strip('"')))
        if part.lower().startswith("filename="):
            value = part.split("=", 1)[1].strip('"')
            return sanitize_filename(unquote(value))

    return sanitize_filename(fallback)
