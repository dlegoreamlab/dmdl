from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(slots=True)
class CompletedEvent:
    task_id: str
    record_id: str
    path: str
    timestamp: float = field(default_factory=time.time)
