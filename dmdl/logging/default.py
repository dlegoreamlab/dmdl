from __future__ import annotations

import json
import logging
from typing import Any


def configure_logging(level: int | str = logging.INFO) -> None:
    root = logging.getLogger("dmdl")
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


class StructuredLogger:
    def __init__(self, name: str = "dmdl") -> None:
        configure_logging()
        self._logger = logging.getLogger(name)

    def _render(self, message: str, **fields: Any) -> str:
        if not fields:
            return message
        payload = json.dumps(fields, ensure_ascii=False, sort_keys=True, default=str)
        return f"{message} | {payload}"

    def _log(self, level: int, message: str, **fields: Any) -> None:
        self._logger.log(level, self._render(message, **fields))

    def debug(self, message: str, **fields: Any) -> None:
        self._log(logging.DEBUG, message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        self._log(logging.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._log(logging.WARNING, message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self._log(logging.ERROR, message, **fields)

    def exception(self, message: str, **fields: Any) -> None:
        self._logger.exception(self._render(message, **fields))

    def event(self, event_name: str, **fields: Any) -> None:
        self.info(f"event::{event_name}", **fields)


def get_logger(name: str = "dmdl") -> StructuredLogger:
    return StructuredLogger(name=name)
