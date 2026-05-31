from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .meta_schema import META_SCHEMA


VALID_RECORD_TYPES = set(META_SCHEMA.keys())


def allowed_meta_keys(record_type: str) -> List[str]:
    schema = META_SCHEMA.get(record_type, {})
    keys: List[str] = []
    for group_keys in schema.values():
        if isinstance(group_keys, list):
            keys.extend(group_keys)
    return keys


@dataclass
class FileRecord:
    id: str
    node_id: str
    global_id: str
    path: str
    created_at: float
    updated_at: float
    last_seen: float
    type: str
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in VALID_RECORD_TYPES:
            raise ValueError(
                f"Unsupported record type '{self.type}'. "
                f"Supported types: {sorted(VALID_RECORD_TYPES)}"
            )

    @property
    def schema_keys(self) -> List[str]:
        return allowed_meta_keys(self.type)

    def normalize_meta(self, keep_unknown: bool = True) -> Dict[str, Any]:
        allowed = set(self.schema_keys)
        if keep_unknown:
            return dict(self.meta)
        return {k: v for k, v in self.meta.items() if k in allowed}

    def update_meta(self, values: Mapping[str, Any], keep_unknown: bool = True) -> None:
        merged = dict(self.meta)
        merged.update(dict(values))
        self.meta = merged if keep_unknown else {
            k: v for k, v in merged.items() if k in set(self.schema_keys)
        }
        self.touch()

    def touch(self, ts: Optional[float] = None) -> None:
        import time

        now = ts if ts is not None else time.time()
        self.updated_at = now
        self.last_seen = now

    def to_dict(self, keep_unknown_meta: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        data["meta"] = self.normalize_meta(keep_unknown=keep_unknown_meta)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FileRecord":
        return cls(**dict(data))
