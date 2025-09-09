# fastapi_sse/events.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import json
import time
import uuid

@dataclass
class SSEEvent:
    """
    Represent a single SSE message.
    """
    data: Any
    event: Optional[str] = None
    id: Optional[str] = None
    retry: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def encode(self) -> str:
        """
        Encode as text/event-stream format.
        """
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.event:
            lines.append(f"event: {self.event}")
        # Data should be JSON-serialized if not a string
        if not isinstance(self.data, str):
            payload = json.dumps(self.data, default=str, ensure_ascii=False)
        else:
            payload = self.data
        # split multiline
        for ln in payload.splitlines():
            lines.append(f"data: {ln}")
        if self.retry is not None:
            lines.append(f"retry: {self.retry}")
        # optional meta as comments
        if self.meta:
            for k, v in self.meta.items():
                lines.append(f":meta {k}={v}")
        lines.append("")  # terminate with blank line
        return "\n".join(lines)
