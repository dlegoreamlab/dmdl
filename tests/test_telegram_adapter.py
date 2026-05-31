from pathlib import Path

from dmdl.adapters.telegram_adapter import TelegramAdapter
from dmdl.core.manager import DownloadManager
from dmdl.models.download_task import DownloadTask


class DummyAdapter:
    name = "dummy"


def test_telegram_adapter_can_handle_t_me_links() -> None:
    adapter = TelegramAdapter()
    task = DownloadTask(url="https://t.me/example/42", requested_type="video")
    assert adapter.can_handle(task) is True


def test_telegram_adapter_resolves_message_ids_from_url_and_range() -> None:
    adapter = TelegramAdapter()
    task = DownloadTask(url="https://t.me/example/42", requested_type="video")
    cfg = {
        "from_message_id": 40,
        "to_message_id": 42,
        "range_limit": 10,
    }
    assert adapter._resolve_message_ids(task, cfg) == [42, 40, 41]


def test_telegram_adapter_infers_record_type_from_media() -> None:
    adapter = TelegramAdapter()
    assert adapter._infer_record_type("video/mp4", Path("sample.mp4")) == "video"
    assert adapter._infer_record_type("audio/mpeg", Path("sample.mp3")) == "music"
    assert adapter._infer_record_type("image/jpeg", Path("sample.jpg")) == "image"


def test_manager_prefers_detected_record_type_metadata() -> None:
    manager = DownloadManager(auto_load_plugins=False)
    inferred = manager._infer_type(
        saved_path="downloads/telegram_manifest.json",
        adapter=DummyAdapter(),
        metadata={"detected_record_type": "video", "content_type": "application/json"},
    )
    assert inferred == "video"
