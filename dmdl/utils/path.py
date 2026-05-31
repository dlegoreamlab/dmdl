from __future__ import annotations

from pathlib import Path

from .filename import sanitize_filename


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def ensure_unique_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    parent = candidate.parent

    counter = 1
    while True:
        next_candidate = parent / f"{stem}_{counter}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        counter += 1


def build_output_path(directory: str | Path, filename: str, *, unique: bool = True) -> Path:
    directory = ensure_dir(directory)
    sanitized = sanitize_filename(filename)
    path = directory / sanitized
    return ensure_unique_path(path) if unique else path
