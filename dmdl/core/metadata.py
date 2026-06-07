from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from dfss import FileRecord, SchemaRegistry

from ..utils.hashing import stable_hash

_DFSS_SECTION_KEYS = {
    "_schema",
    "fields",
    "content",
    "semantic",
    "relation",
    "structure",
    "authentication",
    "media",
    "analysis",
    "scoring",
    "recommend",
    "gps",
    "feature",
    "map",
}

_MISSING = object()

_FIELD_RULES: dict[str, list[tuple[str, str]]] = {
    "title": [("fields", "title")],
    "author": [("fields", "author")],
    "published_at": [("fields", "published_at")],
    "summary": [("fields", "summary"), ("content", "summary")],
    "source": [("fields", "source")],
    "language": [("fields", "language")],
    "default_language": [("fields", "language")],
    "source_url": [("fields", "source_url"), ("relation", "source_url")],
    "snippet": [("fields", "snippet"), ("content", "excerpt")],
    "excerpt": [("content", "excerpt")],
    "full_text": [("content", "full_text")],
    "description": [("content", "description")],
    "transcript": [("content", "transcript")],
    "caption": [("content", "excerpt")],
    "topics": [("semantic", "topics")],
    "keywords": [("semantic", "keywords")],
    "tags": [("semantic", "keywords")],
    "entities": [("semantic", "entities")],
    "embedding": [("feature", "embedding"), ("semantic", "embedding")],
    "scene": [("feature", "scene")],
    "objects": [("feature", "objects")],
    "dominant_color": [("feature", "dominant_color")],
    "quality": [("scoring", "quality")],
    "relevance": [("scoring", "relevance")],
    "confidence": [("scoring", "confidence")],
    "page_count": [("fields", "page_count")],
    "view_count": [("fields", "view_count")],
    "channel_title": [("fields", "channel")],
    "duration": [("fields", "duration_sec"), ("fields", "duration")],
    "codec": [("fields", "codec")],
    "width": [("fields", "width")],
    "height": [("fields", "height")],
    "fps": [("fields", "fps")],
    "size": [("fields", "size")],
    "filename": [("fields", "file_name")],
    "file_name": [("fields", "file_name")],
    "content_type": [("fields", "mime_type")],
    "mime_type": [("fields", "mime_type")],
    "thumbnail_path": [("relation", "thumbnail_path")],
    "webpage_url": [("relation", "video_url"), ("relation", "source_url")],
    "source_platform": [("relation", "platform")],
    "source_type": [("relation", "platform")],
    "telegram_chat_id": [("relation", "chat_id")],
    "play_score": [("fields", "play_score")],
    "artist": [("fields", "artist")],
    "album": [("fields", "album")],
    "genre": [("fields", "genre")],
    "format": [("fields", "format")],
    "camera": [("fields", "camera")],
    "created_at": [("fields", "created_at")],
    "lat": [("gps", "lat")],
    "lon": [("gps", "lon")],
    "alt": [("gps", "alt")],
    "tile": [("map", "tile")],
    "geohash": [("map", "geohash")],
    "region": [("map", "region")],
}


class MetadataManager:
    def __init__(self, node_id: str = "local") -> None:
        self.node_id = node_id

    def filter_meta(self, record_type: str, values: Mapping[str, Any]) -> Dict[str, Any]:
        if not SchemaRegistry.exists(record_type):
            return {}

        schema = SchemaRegistry.get(record_type).sections
        raw = dict(values or {})
        if any(key in _DFSS_SECTION_KEYS for key in raw):
            return self._sanitize_sectioned_meta(schema, raw)
        return self._normalize_flat_meta(schema, raw)

    def build_record(
        self,
        *,
        source_url: str,
        path: str,
        record_type: str,
        meta: Optional[Mapping[str, Any]] = None,
    ) -> FileRecord:
        if not SchemaRegistry.exists(record_type):
            raise ValueError(f"Unsupported record type: {record_type}")

        now = time.time()
        merged_meta = dict(meta or {})
        merged_meta.setdefault("source_url", source_url)
        merged_meta.setdefault("filename", Path(path).name)
        normalized_meta = self.filter_meta(record_type, merged_meta)
        global_id = stable_hash(f"{source_url}|{path}|{record_type}")
        record_id = stable_hash(f"record|{global_id}", length=16)

        record = FileRecord.create(
            path=str(Path(path)),
            type=record_type,
            meta=normalized_meta,
            node_id=self.node_id,
            global_id=global_id,
            record_id=record_id,
        )
        record.created_at = now
        record.updated_at = now
        record.last_seen = now
        record.validate()
        return record

    def _sanitize_sectioned_meta(
        self,
        schema: Mapping[str, Mapping[str, Any]],
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for section_name, section_fields in schema.items():
            section_value = values.get(section_name)
            if not isinstance(section_value, Mapping):
                continue
            for field_name, expected_type in section_fields.items():
                if field_name not in section_value:
                    continue
                coerced = self._coerce_value(expected_type, section_value[field_name])
                if coerced is _MISSING:
                    continue
                normalized.setdefault(section_name, {})[field_name] = coerced
        return normalized

    def _normalize_flat_meta(
        self,
        schema: Mapping[str, Mapping[str, Any]],
        values: Mapping[str, Any],
    ) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        mutable_values = dict(values)

        if "fields" in schema and "file_name" in schema["fields"] and not mutable_values.get("filename"):
            path_value = mutable_values.get("path")
            if isinstance(path_value, str) and path_value:
                mutable_values["filename"] = Path(path_value).name

        if (
            "relation" in schema
            and "message_id" in schema["relation"]
            and "telegram_message_ids" in mutable_values
            and not mutable_values.get("message_id")
        ):
            message_ids = mutable_values.get("telegram_message_ids")
            if isinstance(message_ids, list) and len(message_ids) == 1:
                mutable_values["message_id"] = message_ids[0]

        channel_id = mutable_values.get("channel_id")
        if channel_id and not mutable_values.get("channel_url"):
            mutable_values["channel_url"] = f"https://www.youtube.com/channel/{channel_id}"

        for source_key, targets in _FIELD_RULES.items():
            if source_key not in mutable_values:
                continue
            value = mutable_values[source_key]
            for section_name, field_name in targets:
                section_fields = schema.get(section_name)
                if not section_fields or field_name not in section_fields:
                    continue
                coerced = self._coerce_value(section_fields[field_name], value)
                if coerced is _MISSING:
                    continue
                normalized.setdefault(section_name, {})[field_name] = coerced
                break

        return normalized

    def _coerce_value(self, expected_type: Any, value: Any) -> Any:
        if value is None:
            return _MISSING
        if expected_type is object:
            return value
        if isinstance(expected_type, tuple):
            for candidate in expected_type:
                coerced = self._coerce_value(candidate, value)
                if coerced is not _MISSING:
                    return coerced
            return _MISSING
        if expected_type is str:
            return str(value)
        if expected_type is list:
            if isinstance(value, list):
                return value
            if isinstance(value, (tuple, set)):
                return list(value)
            return [value]
        if expected_type is int:
            if isinstance(value, bool):
                return _MISSING
            try:
                return int(value)
            except (TypeError, ValueError):
                return _MISSING
        if expected_type is float:
            if isinstance(value, bool):
                return _MISSING
            try:
                return float(value)
            except (TypeError, ValueError):
                return _MISSING
        if isinstance(value, expected_type):
            return value
        return _MISSING
