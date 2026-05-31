from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from ..models.meta_schema import META_SCHEMA
from ..models.schema import FileRecord, allowed_meta_keys
from ..utils.hashing import stable_hash


class MetadataManager:
    def __init__(self, node_id: str = "local") -> None:
        self.node_id = node_id

    def filter_meta(self, record_type: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        allowed = set(allowed_meta_keys(record_type))
        return {k: v for k, v in values.items() if k in allowed}

    def build_record(
        self,
        *,
        source_url: str,
        path: str,
        record_type: str,
        meta: Optional[Mapping[str, Any]] = None,
    ) -> FileRecord:
        if record_type not in META_SCHEMA:
            raise ValueError(f"Unsupported record type: {record_type}")

        now = time.time()
        normalized_meta = self.filter_meta(record_type, meta or {})
        global_id = stable_hash(f"{source_url}|{path}|{record_type}")
        record_id = stable_hash(f"record|{global_id}", length=16)

        return FileRecord(
            id=record_id,
            node_id=self.node_id,
            global_id=global_id,
            path=str(Path(path)),
            created_at=now,
            updated_at=now,
            last_seen=now,
            type=record_type,
            meta=normalized_meta,
        )
