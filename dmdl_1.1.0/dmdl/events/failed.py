from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class FailedEvent:
    task_id: str
    error: str
    timestamp: float = field(default_factory=time.time)
