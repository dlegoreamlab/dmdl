from __future__ import annotations

from ..adapters.direct_adapter import DirectAdapter
from ..adapters.generic_adapter import GenericAdapter
from ..adapters.ytdlp_adapter import YtDlpAdapter
from .base import AdapterProtocol


def get_builtin_adapters() -> list[AdapterProtocol]:
    return [YtDlpAdapter(), DirectAdapter(), GenericAdapter()]
