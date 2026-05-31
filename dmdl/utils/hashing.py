from __future__ import annotations

import hashlib


def stable_hash(value: str, algorithm: str = "sha1", length: int = 40) -> str:
    digest = hashlib.new(algorithm)
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()[:length]
