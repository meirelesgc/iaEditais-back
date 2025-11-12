import asyncio
import json
from typing import Dict
from uuid import UUID

from fastapi import WebSocket
from redis.asyncio import Redis

from iaEditais.core.settings import Settings
from iaEditais.schemas import WSMessage

SETTINGS = Settings()


class ConnectionManager:
    def __init__(
        self,
        redis_url: str = 'redis://localhost:6379',
        channel: str = 'ws:broadcast',
    ):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.channel = channel
        self._pubsub_task = None

    async def connect(self, client_id: UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if not self._pubsub_task:
            self._pubsub_task = asyncio.create_task(
                self._listen_to_broadcasts()
            )

    def disconnect(self, client_id: UUID):
        self.active_connections.pop(client_id, None)

    async def send_personal_message(self, client_id: UUID, message: WSMessage):
        ws = self.active_connections.get(client_id)
        if ws:
            await ws.send_json(message.model_dump())

    async def broadcast(self, message: WSMessage):
        data = message.model_dump_json()
        await self.redis.publish(self.channel, data)

    async def _listen_to_broadcasts(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self.channel)
        async for msg in pubsub.listen():
            if msg and msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    ws_message = WSMessage(**data)
                    await self._local_broadcast(ws_message)
                except Exception:
                    continue

    async def _local_broadcast(self, message: WSMessage):
        for ws in list(self.active_connections.values()):
            try:
                await ws.send_json(message.model_dump())
            except Exception:
                continue


manager = ConnectionManager(redis_url=SETTINGS.CACHE_URL)
