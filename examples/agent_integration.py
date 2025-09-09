# examples/agent_integration.py
import asyncio
from fastapi import FastAPI, Request
from fastapi_sse.core import SSEManager
from fastapi_sse.events import SSEEvent
from typing import Dict

app = FastAPI()
manager = SSEManager(app=app, keepalive_interval=10.0, max_history=200)
app.add_api_route("/sse/agent/{client_id}", manager.endpoint("agent"), methods=["GET"])

async def fake_agent_stream(prompt: str):
    """
    Simulate token-by-token generation; in real use you'd stream from the model API.
    """
    for i, token in enumerate(["Hello", ",", " this", " is", " a", " streamed", " reply", "."]):
        await asyncio.sleep(0.5)
        yield token

@app.post("/agent/send/{conversation_id}")
async def agent_send(conversation_id: str, payload: Dict):
    """
    API that initiates agent generation and streams tokens to channel subscribers.
    """
    ch = manager.channel("agent")
    # broadcast the 'start' marker
    start_ev = SSEEvent(data={"conversation_id": conversation_id, "status": "started"}, event="agent.start")
    await ch.send(start_ev)

    async def run_generation():
        async for token in async_generator_wrapper(fake_agent_stream(payload.get("prompt", ""))):
            ev = SSEEvent(data={"conversation_id": conversation_id, "token": token}, event="agent.token")
            await ch.send(ev)
        done_ev = SSEEvent(data={"conversation_id": conversation_id, "status": "done"}, event="agent.done")
        await ch.send(done_ev)

    # start in background so HTTP returns quickly (or you could await)
    asyncio.create_task(run_generation())
    return {"started": True}

# helper to adapt sync generator to async
async def async_generator_wrapper(gen):
    for v in gen:
        yield v
