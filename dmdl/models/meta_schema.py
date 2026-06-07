from __future__ import annotations

from dfss import SchemaRegistry


META_SCHEMA = {
    record_type: {
        section_name: list(section_fields.keys())
        for section_name, section_fields in SchemaRegistry.get(record_type).sections.items()
    }
    for record_type in SchemaRegistry.types()
}


__all__ = ["META_SCHEMA"]
