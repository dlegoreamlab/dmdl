from __future__ import annotations

from typing import List

from dfss import FileRecord, SchemaRegistry


VALID_RECORD_TYPES = set(SchemaRegistry.types())


def allowed_meta_keys(record_type: str) -> List[str]:
    if not SchemaRegistry.exists(record_type):
        return []

    definition = SchemaRegistry.get(record_type)
    keys: List[str] = []
    for section_fields in definition.sections.values():
        keys.extend(section_fields.keys())
    return keys


__all__ = [
    "FileRecord",
    "VALID_RECORD_TYPES",
    "allowed_meta_keys",
]
