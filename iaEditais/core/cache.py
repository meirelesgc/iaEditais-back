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

    async def connect(self, client_id: UUID, websocket: WebSocket):
        await websocket.accept()
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

    async def local_broadcast_async(self, message: WSMessage):
        """Envia mensagem para todos os WebSockets conectados de forma assincrona."""
        for client_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_json(message.model_dump())
            except Exception:
                # Remove conexao morta
                self.active_connections.pop(client_id, None)

    async def start_redis_listener(self):
        """Inicia listener do Redis pub/sub em background."""
        import asyncio
        import queue
        import threading

        msg_queue = queue.Queue()

        def redis_thread():
            pubsub = self.redis.pubsub()
            pubsub.subscribe(self.channel)
            for msg in pubsub.listen():
                if msg and msg['type'] == 'message':
                    msg_queue.put(msg['data'])

        # Inicia thread do Redis (bloqueante)
        thread = threading.Thread(target=redis_thread, daemon=True)
        thread.start()
        print('DEBUG: Redis listener iniciado')

        # Loop principal (async)
        while True:
            try:
                data = msg_queue.get_nowait()
                ws_message = WSMessage.model_validate_json(data)
                await self.local_broadcast_async(ws_message)
                print(
                    f'DEBUG: Broadcast enviado para {len(self.active_connections)} clientes'
                )
            except queue.Empty:
                await asyncio.sleep(0.05)
            except Exception as e:
                print(f'DEBUG: Erro no listener: {e}')
                continue


# Instancia global (singleton)
_manager_instance = None


def get_cache():  # pragma: no cover
    global _manager_instance
    if _manager_instance is None:
        redis = Redis.from_url(SETTINGS.CACHE_URL)
        _manager_instance = ConnectionManager(redis=redis)
    return _manager_instance
