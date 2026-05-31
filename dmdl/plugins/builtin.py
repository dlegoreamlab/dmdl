from __future__ import annotations

from ..adapters.direct_adapter import DirectAdapter
from ..adapters.generic_adapter import GenericAdapter
from ..adapters.telegram_adapter import TelegramAdapter
from ..adapters.ytdlp_adapter import YtDlpAdapter
from .base import AdapterProtocol


def get_builtin_adapters() -> list[AdapterProtocol]:
    return [TelegramAdapter(), YtDlpAdapter(), DirectAdapter(), GenericAdapter()]
