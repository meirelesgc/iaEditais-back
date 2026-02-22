from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from iaEditais.core.cache import WebSocketManager, get_socket_manager
from iaEditais.schemas import WSMessage

router = APIRouter(prefix='/ws', tags=['websockets'])


@router.websocket('/{subscriber_id}')
async def websocket_endpoint(
    websocket: WebSocket,
    subscriber_id: UUID,
    socket_manager: WebSocketManager = Depends(get_socket_manager),
):
    channel_id = 'ws:broadcast'
    await socket_manager.add_user_to_channel(channel_id, websocket)

    message = WSMessage(
        event='user.connect',
        message=f'User {subscriber_id} connected to channel - {channel_id}',
        payload={},
    )
    await socket_manager.broadcast_to_channel(
        channel_id, message.model_dump_json()
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = WSMessage(event='user.connect', message=data, payload={})
            await socket_manager.broadcast_to_channel(
                channel_id, message.model_dump_json()
            )
    except WebSocketDisconnect:
        await socket_manager.remove_user_from_channel(channel_id, websocket)
        message = WSMessage(
            event='user.disconnect',
            message=f'User {subscriber_id} disconnected to channel - {channel_id}',
            payload={},
        )
        await socket_manager.broadcast_to_channel(
            channel_id, message.model_dump_json()
        )
