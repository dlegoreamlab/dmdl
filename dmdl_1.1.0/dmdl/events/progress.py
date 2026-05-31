from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class ProgressEvent:
    task_id: str
    stage: str
    progress: float
    message: str = ""
    path: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
