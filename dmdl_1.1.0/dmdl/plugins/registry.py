from __future__ import annotations

from typing import Iterable, Sequence

from ..logging import LoggerProtocol, get_logger
from ..models.download_task import DownloadTask
from .base import AdapterProtocol, validate_adapter
from .builtin import get_builtin_adapters
from .loader import load_adapter, load_entrypoint_adapters


class AdapterRegistry:
    def __init__(self, adapters: Sequence[object] | None = None, logger: LoggerProtocol | None = None) -> None:
        self.logger = logger or get_logger("dmdl.plugins")
        self._adapters: list[AdapterProtocol] = []
        if adapters:
            self.set_adapters(adapters)

    @property
    def adapters(self) -> list[AdapterProtocol]:
        return list(self._adapters)

    def set_adapters(self, adapters: Sequence[object]) -> None:
        self._adapters = []
        self.register_many(adapters)

    def register(self, adapter: object, *, prepend: bool = False) -> AdapterProtocol:
        validated = validate_adapter(adapter)
        self.unregister(validated.name)
        if prepend:
            self._adapters.insert(0, validated)
        else:
            self._adapters.append(validated)
        self.logger.debug("adapter registered", adapter=validated.name, prepend=prepend)
        return validated

    def register_many(self, adapters: Iterable[object], *, prepend: bool = False) -> list[AdapterProtocol]:
        registered: list[AdapterProtocol] = []
        for adapter in adapters:
            registered.append(self.register(adapter, prepend=prepend))
        return registered

    def unregister(self, name: str) -> None:
        before = len(self._adapters)
        self._adapters = [adapter for adapter in self._adapters if adapter.name != name]
        if len(self._adapters) != before:
            self.logger.debug("adapter unregistered", adapter=name)

    def get(self, name: str) -> AdapterProtocol:
        for adapter in self._adapters:
            if adapter.name == name:
                return adapter
        raise ValueError(f"Unknown adapter_hint: {name}")

    def pick(self, task: DownloadTask) -> AdapterProtocol:
        if task.adapter_hint:
            return self.get(task.adapter_hint)
        for adapter in self._adapters:
            if adapter.can_handle(task):
                return adapter
        raise ValueError(f"No adapter available for URL: {task.url}")

    def load_builtin(self, *, replace: bool = False) -> list[AdapterProtocol]:
        adapters = get_builtin_adapters()
        if replace:
            self.set_adapters(adapters)
            return self.adapters
        return self.register_many(adapters)

    def load_entrypoints(self, group: str = "dmdl.adapters", *, prepend: bool = True) -> list[AdapterProtocol]:
        adapters = load_entrypoint_adapters(group=group)
        return self.register_many(adapters, prepend=prepend)

    def load_import_paths(self, import_paths: Iterable[str], *, prepend: bool = True) -> list[AdapterProtocol]:
        registered: list[AdapterProtocol] = []
        for import_path in import_paths:
            registered.append(self.register(load_adapter(import_path), prepend=prepend))
        return registered
