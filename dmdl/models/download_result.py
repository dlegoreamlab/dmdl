from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .schema import FileRecord


@dataclass(slots=True)
class DownloadResult:
    task_id: str
    success: bool
    source_url: str
    adapter: str
    record: Optional[FileRecord] = None
    saved_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    completed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "success": self.success,
            "source_url": self.source_url,
            "adapter": self.adapter,
            "record": self.record.to_dict() if self.record else None,
            "saved_path": self.saved_path,
            "metadata": self.metadata,
            "error": self.error,
            "completed_at": self.completed_at,
        }
