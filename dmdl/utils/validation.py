from __future__ import annotations

from pathlib import Path
from typing import Mapping
from urllib.parse import urlparse


_ALLOWED_URL_SCHEMES = {"http", "https"}
# Non-HTTP schemes used by DICL FileRecord paths (e.g. telegram permalinks for
# private chats where there is no public t.me/<username>/<id> URL).
_ALLOWED_PSEUDO_SCHEMES = {"telegram"}


def validate_http_url(url: str) -> str:
    normalized = str(url).strip()
    parsed = urlparse(normalized)
    if parsed.scheme in _ALLOWED_URL_SCHEMES and parsed.netloc:
        return normalized
    if parsed.scheme in _ALLOWED_PSEUDO_SCHEMES:
        # telegram://chat/<chat_id>/message/<message_id> style permalinks are
        # produced by DICL for chats without a public username. They have no
        # netloc in the http sense, so we only require the scheme + a path.
        if parsed.netloc or parsed.path:
            return normalized
    raise ValueError(
        f"Unsupported URL: {url!r}. Only HTTP/HTTPS or telegram:// URLs are allowed."
    )


def ensure_mapping(value: object, *, field_name: str) -> dict:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping, got {type(value).__name__}.")
    return dict(value)


def normalize_output_dir(path: str | Path) -> str:
    return str(Path(path or "downloads"))
