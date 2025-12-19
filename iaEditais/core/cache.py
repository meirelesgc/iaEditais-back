import asyncio

import redis.asyncio as aioredis
from fastapi import Request, WebSocket
from redis.asyncio import Redis


class PubSubManager:
    def __init__(self, redis: aioredis.Redis):
        self.redis_connection = redis
        self.pubsub = None

    async def connect(self) -> None:
        self.pubsub = self.redis_connection.pubsub()

    async def _publish(self, channel_id: str, message: str) -> None:
        await self.redis_connection.publish(channel_id, message)

    async def subscribe(self, channel_id: str):
        await self.pubsub.subscribe(channel_id)
        return self.pubsub

    async def unsubscribe(self, channel_id: str) -> None:
        await self.pubsub.unsubscribe(channel_id)


class WebSocketManager:
    def __init__(self, client: aioredis.Redis):
        self.channels: dict = {}
        self.pubsub_client = PubSubManager(client)

    async def add_user_to_channel(self, channel_id: str, websocket: WebSocket):
        await websocket.accept()
        if channel_id in self.channels:
            self.channels[channel_id].append(websocket)
        else:
            self.channels[channel_id] = [websocket]

            await self.pubsub_client.connect()
            pubsub_subscriber = await self.pubsub_client.subscribe(channel_id)
            asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))

    async def broadcast_to_channel(self, channel_id: str, message: str):
        await self.pubsub_client._publish(channel_id, message)

    async def remove_user_from_channel(
        self, channel_id: str, websocket: WebSocket
    ):
        self.channels[channel_id].remove(websocket)
        if len(self.channels[channel_id]) == 0:
            del self.channels[channel_id]
            await self.pubsub_client.unsubscribe(channel_id)

    async def _pubsub_data_reader(self, pubsub_subscriber):
        while True:
            message = await pubsub_subscriber.get_message(
                ignore_subscribe_messages=True
            )
            if message is not None:
                channel_id = message['channel'].decode('utf-8')
                all_sockets = self.channels[channel_id]
                for socket in all_sockets:
                    data = message['data'].decode('utf-8')
                    await socket.send_text(data)


def get_socket_manager(websocket: WebSocket) -> WebSocketManager:
    return websocket.app.state.socket_manager


def get_redis(request: Request) -> Redis:
    return request.app.state.redis
