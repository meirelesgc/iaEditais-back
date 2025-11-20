import json
from typing import Dict
from uuid import UUID

from fastapi import WebSocket
from redis import Redis

from iaEditais.core.settings import Settings
from iaEditais.schemas import WSMessage

SETTINGS = Settings()


class ConnectionManager:
    def __init__(self, redis: Redis, channel: str = 'ws:broadcast'):
        self.active_connections: Dict[UUID, WebSocket] = {}
        self.redis = redis
        self.channel = channel

    def connect(self, client_id: UUID, websocket: WebSocket):
        websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: UUID):
        self.active_connections.pop(client_id, None)

    def send_personal_message(self, client_id: UUID, message: WSMessage):
        ws = self.active_connections.get(client_id)
        if ws:
            ws.send_json(message.model_dump())

    def broadcast(self, message: WSMessage):
        data = message.model_dump_json()
        self.redis.publish(self.channel, data)

    def listen_to_broadcasts(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.channel)
        for msg in pubsub.listen():
            if msg and msg['type'] == 'message':
                try:
                    data = json.loads(msg['data'])
                    ws_message = WSMessage(**data)
                    self.local_broadcast(ws_message)
                except Exception:
                    continue

    def local_broadcast(self, message: WSMessage):
        for ws in list(self.active_connections.values()):
            try:
                ws.send_json(message.model_dump())
            except Exception:
                continue


def get_cache():  # pragma: no cover
    redis = Redis.from_url(SETTINGS.CACHE_URL)
    return ConnectionManager(redis=redis)
