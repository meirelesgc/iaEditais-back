import asyncio
from typing import List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


async def cache_listener(cache_client):
    pubsub = cache_client.pubsub()
    await pubsub.subscribe('public')
    while True:
        message = await pubsub.get_message(
            ignore_subscribe_messages=True, timeout=1.0
        )
        if message and message.get('data'):
            data_str = message['data'].decode('utf-8')
            await manager.broadcast(data_str)
        await asyncio.sleep(0.01)
