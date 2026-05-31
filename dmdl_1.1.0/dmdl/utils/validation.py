from __future__ import annotations

from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


_ALLOWED_URL_SCHEMES = {"http", "https"}


def validate_http_url(url: str) -> str:
    normalized = str(url).strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in _ALLOWED_URL_SCHEMES or not parsed.netloc:
        raise ValueError(f"Unsupported URL: {url!r}. Only HTTP/HTTPS URLs are allowed.")
    return normalized


def ensure_mapping(value: object, *, field_name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping, got {type(value).__name__}.")
    return dict(value)


def normalize_output_dir(path: str | Path) -> str:
    return str(Path(path or "downloads"))
