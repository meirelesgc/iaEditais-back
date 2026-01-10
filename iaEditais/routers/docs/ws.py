import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from iaEditais.core.dependencies import CacheManager
from iaEditais.schemas import WSMessage

router = APIRouter(prefix='/ws', tags=['websockets'])


@router.websocket('/{client_id}')
async def websocket_endpoint(
    websocket: WebSocket, client_id: UUID, manager: CacheManager
):
    await manager.connect(client_id, websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                message = WSMessage.model_validate_json(raw_data)
            except Exception:
                message = 'Invalid message format'
                ws_message = WSMessage(event='error', message=message)
                manager.send_personal_message(client_id, ws_message)
                continue
            if message.event == 'ping':
                ws_message = WSMessage(event='pong', message='ok')
                manager.send_personal_message(client_id, ws_message)
            elif message.event == 'broadcast':
                ws_message = WSMessage(
                    event='broadcast',
                    message=message.message,
                    payload=message.payload,
                )
                manager.broadcast(ws_message)
            else:
                ws_message = WSMessage(
                    event='echo',
                    message=message.message,
                    payload=message.payload,
                )
                manager.send_personal_message(client_id, ws_message)
            await asyncio.sleep(0.03)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
