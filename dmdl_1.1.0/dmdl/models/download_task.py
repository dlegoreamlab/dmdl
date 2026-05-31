from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..utils.hashing import stable_hash
from ..utils.validation import ensure_mapping, normalize_output_dir, validate_http_url
from .schema import VALID_RECORD_TYPES


@dataclass(slots=True)
class DownloadTask:
    url: str
    requested_type: Optional[str] = None
    output_dir: str = "downloads"
    adapter_hint: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 100
    created_at: float = field(default_factory=time.time)
    task_id: str = ""

    def __post_init__(self) -> None:
        self.url = validate_http_url(self.url)
        self.output_dir = normalize_output_dir(self.output_dir)
        self.options = ensure_mapping(self.options, field_name="options")
        self.context = ensure_mapping(self.context, field_name="context")

        if self.requested_type and self.requested_type not in VALID_RECORD_TYPES:
            raise ValueError(
                f"Unsupported requested_type '{self.requested_type}'. "
                f"Supported types: {sorted(VALID_RECORD_TYPES)}"
            )

        if not self.task_id:
            self.task_id = stable_hash(
                f"{self.url}|{self.requested_type}|{self.output_dir}|{self.created_at}|{self.priority}",
                length=16,
            )
