# tests/test_core.py
import pytest
import asyncio
from fastapi_sse.core import SSEManager
from fastapi import FastAPI
from fastapi_sse.events import SSEEvent

@pytest.mark.asyncio
async def test_channel_send_receive():
    app = FastAPI()
    manager = SSEManager(app=app, keepalive_interval=0.5)
    ch = manager.channel("t1")
    conn = await ch.connect("client1")
    ev = SSEEvent(data={"x": 1}, event="msg")
    await ch.send(ev)
    received = await conn.queue.get()
    assert received.data == {"x": 1}
    await ch.disconnect("client1")
