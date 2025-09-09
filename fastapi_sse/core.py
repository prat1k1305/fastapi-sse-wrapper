# fastapi_sse/core.py
from __future__ import annotations
import asyncio
from typing import Dict, Callable, Optional, Any, List, Coroutine
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import StreamingResponse
from starlette.concurrency import run_until_first_complete
from .events import SSEEvent
import logging

logger = logging.getLogger("fastapi_sse")

class SSEConnection:
    """
    Represents a single client connection to a channel.
    Each connection has an asyncio.Queue used to push SSEEvent objects.
    """
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
        self.closed = asyncio.Event()

    async def push(self, event: SSEEvent):
        await self.queue.put(event)

    async def close(self):
        self.closed.set()
        # put sentinel to unblock generator
        await self.queue.put(SSEEvent(data="", event="__closed__"))

class SSEChannel:
    """
    Manage many SSEConnection objects and provide send/broadcast.
    """
    def __init__(self, name: str, history_size: int = 50):
        self.name = name
        self.connections: Dict[str, SSEConnection] = {}
        # simple in-memory history
        self.history: List[SSEEvent] = []
        self.history_size = history_size
        self.lock = asyncio.Lock()

    async def connect(self, client_id: str) -> SSEConnection:
        async with self.lock:
            if client_id in self.connections:
                # allow reconnection: close old
                old = self.connections[client_id]
                await old.close()
            conn = SSEConnection(client_id)
            self.connections[client_id] = conn
            logger.debug("Connected client %s to channel %s", client_id, self.name)
            return conn

    async def disconnect(self, client_id: str):
        async with self.lock:
            conn = self.connections.pop(client_id, None)
            if conn:
                await conn.close()
                logger.debug("Disconnected client %s from channel %s", client_id, self.name)

    async def send(self, event: SSEEvent, target_client: Optional[str] = None):
        """
        Send event to a specific client or broadcast when target_client is None.
        """
        # store in history
        self.history.append(event)
        if len(self.history) > self.history_size:
            self.history = self.history[-self.history_size:]

        if target_client:
            conn = self.connections.get(target_client)
            if conn:
                await conn.push(event)
        else:
            # broadcast
            for conn in list(self.connections.values()):
                await conn.push(event)

    def recent(self, limit: Optional[int] = None) -> List[SSEEvent]:
        if limit is None:
            limit = len(self.history)
        return list(self.history[-limit:])

class SSEManager:
    """
    Top-level manager for multiple named channels.
    Provides helper to create streaming endpoints for FastAPI.
    """
    def __init__(
        self,
        app: Optional[FastAPI] = None,
        keepalive_interval: float = 15.0,
        max_history: int = 100,
        auth_hook: Optional[Callable[[Request], Coroutine[Any, Any, Optional[str]]]] = None
    ):
        self.app = app
        self.channels: Dict[str, SSEChannel] = {}
        self.keepalive_interval = keepalive_interval
        self.max_history = max_history
        self.auth_hook = auth_hook

    def channel(self, name: str) -> SSEChannel:
        if name not in self.channels:
            self.channels[name] = SSEChannel(name, history_size=self.max_history)
        return self.channels[name]

    async def _generator(self, conn: SSEConnection, last_event_id: Optional[str] = None):
        """
        A StreamingResponse generator that yields SSE text frames as bytes.
        Emits past history if last_event_id provided (replay).
        """
        # optionally replay events after last_event_id
        # send keepalive pings as needed
        try:
            # first flush recent if last_event_id present
            if last_event_id is not None:
                # naive replay: send events after given id
                for ch in self.channels.values():
                    pass  # no-op (channels looked up in endpoint); manager generator receives conn only
            # send a ready comment
            yield b": connected\n\n"

            while not conn.closed.is_set():
                try:
                    # wait for new event with timeout to emit keepalive
                    ev: SSEEvent = await asyncio.wait_for(conn.queue.get(), timeout=self.keepalive_interval)
                    if ev.event == "__closed__":
                        break
                    payload = ev.encode().encode("utf-8")
                    yield payload
                except asyncio.TimeoutError:
                    # send a ping comment to keep connection alive
                    ping = f": ping\n\n".encode("utf-8")
                    yield ping
        except asyncio.CancelledError:
            logger.debug("Generator cancelled for client %s", conn.client_id)
            raise
        finally:
            # ensure closed
            conn.closed.set()

    def endpoint(self, channel_name: str, *, auth_required: bool = False):
        """
        Returns a FastAPI route function to attach to app.
        Example:
            app.get("/sse/{client_id}")(manager.endpoint("chat"))
        """

        async def sse_endpoint(request: Request, client_id: str):
            # auth hook
            if auth_required and self.auth_hook:
                user_val = await self.auth_hook(request)
                if user_val is None:
                    raise HTTPException(status_code=401, detail="Unauthorized")
            # create/connect
            ch = self.channel(channel_name)
            conn = await ch.connect(client_id=client_id)

            # Optionally replay last events if client requested Last-Event-ID
            last_event_id = request.headers.get("Last-Event-ID")
            if last_event_id:
                # replay events with id > last_event_id (simple scheme)
                for ev in ch.recent():
                    if ev.id != last_event_id:
                        # in practice you'd filter by timestamp or id ordering
                        await conn.push(ev)

            generator = self._generator(conn, last_event_id=last_event_id)

            # StreamingResponse will consume the async generator
            response = StreamingResponse(generator, media_type="text/event-stream")
            # recommended headers
            response.headers["Cache-Control"] = "no-cache"
            response.headers["X-Accel-Buffering"] = "no"
            return response

        return sse_endpoint
