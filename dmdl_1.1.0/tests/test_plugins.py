import asyncio

from dmdl.core.manager import DownloadManager
from dmdl.models.download_task import DownloadTask
from dmdl.plugins import AdapterRegistry


class CaptureLogger:
    def __init__(self) -> None:
        self.messages = []

    def debug(self, message: str, **fields) -> None:
        self.messages.append(("debug", message, fields))

    def info(self, message: str, **fields) -> None:
        self.messages.append(("info", message, fields))

    def warning(self, message: str, **fields) -> None:
        self.messages.append(("warning", message, fields))

    def error(self, message: str, **fields) -> None:
        self.messages.append(("error", message, fields))

    def exception(self, message: str, **fields) -> None:
        self.messages.append(("exception", message, fields))

    def event(self, event_name: str, **fields) -> None:
        self.messages.append(("event", event_name, fields))


class PluginAdapter:
    name = "plugin-pdf"

    def can_handle(self, task: DownloadTask) -> bool:
        return task.url.endswith(".pdf")

    async def download(self, task: DownloadTask):
        await asyncio.sleep(0)
        return {
            "saved_path": "downloads/plugin.pdf",
            "metadata": {
                "content_type": "application/pdf",
                "title": "plugin.pdf",
                "source_url": task.url,
            },
        }


def test_adapter_registry_resolves_adapter_hint() -> None:
    registry = AdapterRegistry(adapters=[PluginAdapter()], logger=CaptureLogger())
    task = DownloadTask(
        url="https://example.com/file.pdf",
        requested_type="pdf",
        adapter_hint="plugin-pdf",
    )

    adapter = registry.pick(task)
    assert adapter.name == "plugin-pdf"


def test_manager_emits_logging_events() -> None:
    logger = CaptureLogger()
    manager = DownloadManager(logger=logger, auto_load_plugins=False)
    manager.adapters = [PluginAdapter()]

    task = DownloadTask(url="https://example.com/file.pdf", requested_type="pdf")
    result = asyncio.run(manager.run_task(task))

    assert result.success is True
    assert any(level == "event" and message == "download_started" for level, message, _ in logger.messages)
    assert any(level == "event" and message == "download_completed" for level, message, _ in logger.messages)
    assert any(level == "debug" and message == "adapter selected" for level, message, _ in logger.messages)
