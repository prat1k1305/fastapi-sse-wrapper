# fastapi_sse/utils.py
import asyncio
import logging

def cancel_task(task: asyncio.Task):
    if not task.done():
        task.cancel()
