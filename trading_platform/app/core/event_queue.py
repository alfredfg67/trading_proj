import asyncio

event_queue = asyncio.Queue()

async def publish(event: dict):
    await event_queue.put(event)