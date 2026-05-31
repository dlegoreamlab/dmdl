from __future__ import annotations

from importlib import import_module
from importlib.metadata import entry_points
from typing import Iterable

from .base import AdapterProtocol, validate_adapter


def load_object(import_path: str) -> object:
    if ":" in import_path:
        module_name, attr_name = import_path.split(":", 1)
    else:
        module_name, attr_name = import_path.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, attr_name)


def load_adapter(import_path: str) -> AdapterProtocol:
    obj = load_object(import_path)
    adapter = obj() if isinstance(obj, type) else obj
    return validate_adapter(adapter)


def load_entrypoint_adapters(group: str = "dmdl.adapters") -> list[AdapterProtocol]:
    discovered: list[AdapterProtocol] = []
    for entry_point in entry_points().select(group=group):
        loaded = entry_point.load()
        adapter = loaded() if isinstance(loaded, type) else loaded
        discovered.append(validate_adapter(adapter))
    return discovered


def load_adapters(import_paths: Iterable[str]) -> list[AdapterProtocol]:
    return [load_adapter(path) for path in import_paths]
