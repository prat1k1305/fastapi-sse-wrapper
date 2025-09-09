# examples/simple_app.py
import uvicorn
from fastapi import FastAPI
from fastapi_sse.core import SSEManager
from fastapi_sse.events import SSEEvent
import asyncio

app = FastAPI(title="SSE Example")

manager = SSEManager(app=app, keepalive_interval=10.0)

# mount endpoint for channel "chat"
app.add_api_route("/sse/chat/{client_id}", manager.endpoint("chat"), methods=["GET"])

@app.post("/send/{channel}")
async def send_message(channel: str, payload: dict):
    ch = manager.channel(channel)
    ev = SSEEvent(data=payload, event="message")
    await ch.send(ev)
    return {"status": "ok", "id": ev.id}

# Simple periodic broadcaster for demo
@app.on_event("startup")
async def start_background_broadcaster():
    async def broadcaster():
        c = manager.channel("chat")
        i = 0
        while True:
            await asyncio.sleep(20)
            ev = SSEEvent(data={"msg": f"heartbeat {i}"}, event="heartbeat")
            await c.send(ev)
            i += 1
    asyncio.create_task(broadcaster())

if __name__ == "__main__":
    uvicorn.run("examples.simple_app:app", host="127.0.0.1", port=8000, reload=True)
