# fastapi_sse/backends.py
from typing import Protocol, List, Optional
from .events import SSEEvent

class HistoryBackend(Protocol):
    async def append(self, channel: str, event: SSEEvent) -> None: ...
    async def get_recent(self, channel: str, limit: int) -> List[SSEEvent]: ...

class InMemoryHistory:
    def __init__(self):
        self.store = {}

    async def append(self, channel: str, event: SSEEvent):
        self.store.setdefault(channel, []).append(event)

    async def get_recent(self, channel: str, limit: int = 50):
        lst = self.store.get(channel, [])
        return lst[-limit:]
