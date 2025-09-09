# fastapi-sse-wrapper

A small, professional SSE (Server-Sent Events) wrapper for FastAPI, designed to help developers build streaming AI agent and chatbot backends.

---

## ✨ Features

* **Named channels** with multiple client connections
* **Broadcast** and **targeted messages**
* **Message history & replay** for reconnection support
* **Keepalive pings** and recommended HTTP headers
* **Authentication hooks** (pluggable)
* **Minimal dependencies** (FastAPI + Uvicorn)
* **Typed public API** and examples

---

## 📦 Installation

```bash
pip install fastapi-sse-wrapper
```

---

## 🚀 Quick Start

### Create SSE Manager and Endpoint

```python
from fastapi import FastAPI
from fastapi_sse.core import SSEManager
from fastapi_sse.events import SSEEvent

app = FastAPI()
manager = SSEManager(app=app)

# Register SSE endpoint for channel "chat"
app.add_api_route("/sse/chat/{client_id}", manager.endpoint("chat"), methods=["GET"])
```

### Send Events

```python
@app.post("/send/{channel}")
async def send_message(channel: str, payload: dict):
    ch = manager.channel(channel)
    ev = SSEEvent(data=payload, event="message")
    await ch.send(ev)
    return {"status": "ok", "id": ev.id}
```

### Connect Client

Browser client using **EventSource**:

```js
const es = new EventSource("http://127.0.0.1:8000/sse/chat/myclient");
es.onmessage = e => console.log("msg", e.data);
es.addEventListener("message", e => console.log("event:message", e.data));
```

---

## 🧠 Example: Streaming AI Agent Tokens

```python
@app.post("/agent/send/{conversation_id}")
async def agent_send(conversation_id: str, payload: dict):
    ch = manager.channel("agent")
    start = SSEEvent(data={"cid": conversation_id, "status": "started"}, event="agent.start")
    await ch.send(start)

    for token in ["Hello", ",", " this", " is", " streamed"]:
        await asyncio.sleep(0.5)
        ev = SSEEvent(data={"cid": conversation_id, "token": token}, event="agent.token")
        await ch.send(ev)

    done = SSEEvent(data={"cid": conversation_id, "status": "done"}, event="agent.done")
    await ch.send(done)
    return {"started": True}
```

---

## 🔒 Authentication

Use an auth hook:

```python
from fastapi_sse.middleware import token_auth_hook_factory

def token_lookup(token: str):
    return "user1" if token == "secret" else None

manager = SSEManager(app, auth_hook=token_auth_hook_factory(token_lookup))
```

---

## 📂 Project Structure

```
fastapi-sse-wrapper/
├─ fastapi_sse/
│  ├─ core.py         # Manager + connections
│  ├─ events.py       # SSEEvent model
│  ├─ middleware.py   # Auth hook helpers
│  ├─ backends.py     # In-memory history backend
│  └─ utils.py
├─ examples/
│  ├─ simple_app.py
│  └─ agent_integration.py
├─ tests/
└─ README.md
```

---

## ⚡ Roadmap

* Redis backend for multi-worker support
* Advanced reconnection + replay strategies
* Rate limiting and access control
* TypeScript/JS client SDK

---

## 📜 License

MIT License.







