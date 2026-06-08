"""Tests for the DICL -> DMDL FileRecord bridge added by the dicl-bridge patch.

These tests stay at the unit level so they do not require Telethon or a live
Telegram session: they only verify URL/scheme validation, adapter routing and
``DownloadTask`` shaping based on a DICL-style ``FileRecord`` payload.
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

from dmdl.adapters.telegram_adapter import TelegramAdapter
from dmdl.core.downloader import Downloader, _extract_file_record_fields
from dmdl.models.download_task import DownloadTask
from dmdl.utils.validation import validate_http_url


# ----------------------------------------------------------------------
# URL / scheme validation
# ----------------------------------------------------------------------
def test_validate_http_url_accepts_telegram_scheme() -> None:
    url = "telegram://chat/123456789/message/42"
    assert validate_http_url(url) == url


def test_validate_http_url_still_rejects_unknown_scheme() -> None:
    with pytest.raises(ValueError):
        validate_http_url("ftp://example.com/file.bin")


# ----------------------------------------------------------------------
# TelegramAdapter accepts telegram:// permalinks
# ----------------------------------------------------------------------
def test_telegram_adapter_handles_telegram_scheme() -> None:
    adapter = TelegramAdapter()
    task = DownloadTask(
        url="telegram://chat/123456789/message/42",
        requested_type="video",
    )
    assert adapter.can_handle(task) is True


def test_telegram_adapter_extracts_message_id_from_telegram_scheme() -> None:
    adapter = TelegramAdapter()
    task = DownloadTask(
        url="telegram://chat/123456789/message/42",
        requested_type="video",
    )
    assert adapter._resolve_message_ids(task, cfg={}) == [42]


def test_telegram_adapter_extracts_message_id_from_dicl_relation() -> None:
    adapter = TelegramAdapter()
    task = DownloadTask(
        url="telegram://chat/123456789/message/0",  # path id is fake (0)
        requested_type="video",
        context={
            "dicl_relation": {
                "platform": "telegram",
                "chat_id": 123456789,
                "message_id": 99,
            }
        },
    )
    # relation provides 99, URL path provides 0 (filtered out as <= 0)
    assert adapter._resolve_message_ids(task, cfg={}) == [99]


def test_telegram_adapter_normalize_chat_id_for_channels() -> None:
    assert TelegramAdapter._normalize_chat_id(123456789) == 123456789
    # Positive integer string is treated as a raw channel id and gets the
    # -100 prefix expected by Telethon.
    assert TelegramAdapter._normalize_chat_id("123456789") == -100123456789
    # Negative ids are already in Telethon form.
    assert TelegramAdapter._normalize_chat_id(-100123456789) == -100123456789
    # Username-like strings pass through untouched.
    assert TelegramAdapter._normalize_chat_id("example_channel") == "example_channel"


# ----------------------------------------------------------------------
# Downloader bridge helpers
# ----------------------------------------------------------------------
def _sample_dicl_record(url: str = "telegram://chat/123456789/message/42") -> Dict[str, Any]:
    return {
        "path": url,
        "type": "video",
        "meta": {
            "fields": {
                "file_name": "telegram_-100123456789_42.mp4",
                "size": 10485760,
                "mime_type": "video/mp4",
            },
            "relation": {
                "platform": "telegram",
                "chat_id": 123456789,
                "message_id": 42,
            },
        },
    }


def test_extract_file_record_fields_from_dict() -> None:
    record = _sample_dicl_record()
    path, record_type, meta = _extract_file_record_fields(record)
    assert path == record["path"]
    assert record_type == "video"
    assert meta["relation"]["chat_id"] == 123456789


def test_task_kwargs_from_file_record_forwards_relation_into_context() -> None:
    record = _sample_dicl_record()
    kwargs = Downloader._task_kwargs_from_file_record(
        record,
        output_dir=None,
        adapter_hint="telegram",
        options=None,
        context=None,
        priority=100,
    )
    assert kwargs["url"] == record["path"]
    assert kwargs["adapter_hint"] == "telegram"
    assert kwargs["requested_type"] == "video"
    relation = kwargs["context"]["dicl_relation"]
    assert relation["chat_id"] == 123456789
    assert relation["message_id"] == 42
    assert kwargs["context"]["dicl_file_name"] == record["meta"]["fields"]["file_name"]


def test_task_kwargs_maps_dicl_audio_to_music() -> None:
    record = _sample_dicl_record()
    record["type"] = "audio"
    kwargs = Downloader._task_kwargs_from_file_record(
        record,
        output_dir=None,
        adapter_hint="telegram",
        options=None,
        context=None,
        priority=100,
    )
    # DMDL has no "audio" type; ensure we collapse it to "music".
    assert kwargs["requested_type"] == "music"
