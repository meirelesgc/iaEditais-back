from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

from iaEditais.core.cache import WebSocketManager, get_socket_manager
from iaEditais.core.dependencies import CurrentUser, Model, Session, VStore
from iaEditais.core.security import get_current_user
from iaEditais.schemas import (
    DocumentMessageCreate,
    DocumentMessageList,
    DocumentMessagePublic,
    DocumentMessageUpdate,
)
from iaEditais.schemas.common import WSMessage
from iaEditais.schemas.document_message import (
    DocumentMessageAIResponse,
    MessageEntityType,
    MessageFilter,
    MessageMention,
    ResolvedCitation,
)
from iaEditais.services import ai_service, message_service

router = APIRouter(prefix='/doc', tags=['document verification, messages'])


@router.post(
    '/{doc_id}/message',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentMessagePublic,
)
async def create_document_message(
    doc_id: UUID,
    msg: DocumentMessageCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await message_service.create_message(
        session, current_user.id, doc_id, msg
    )


@router.post(
    '/{doc_id}/message/ai',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentMessageAIResponse,
)
async def create_document_ai_message(
    doc_id: UUID,
    msg: DocumentMessageCreate,
    session: Session,
    model: Model,
    vstore: VStore,
    current_user: CurrentUser,
):
    user_msg = await message_service.create_message(
        session, current_user.id, doc_id, msg
    )

    filters = MessageFilter(limit=10)
    recent_messages = await message_service.list_messages(
        session, doc_id, filters
    )

    response = await ai_service.create_ai_response(
        session=session,
        user_id=current_user.id,
        doc_id=doc_id,
        data=msg,
        model=model,
        vstore=vstore,
        recent_messages=recent_messages,
    )

    ai_data = DocumentMessageCreate(
        content=response['answer'],
        mentions=[MessageMention(id=doc_id, type=MessageEntityType.AI, label='OiacIA')],
        quoted_message=None,
    )
    ai_msg = await message_service.create_message(
        session=session,
        user_id=current_user.id,
        doc_id=doc_id,
        data=ai_data,
        references=response['references'],
    )

    references = [
        ResolvedCitation(**ref) for ref in response['references']
    ]

    return DocumentMessageAIResponse(
        message=ai_msg,
        references=references,
    )


@router.get(
    '/{doc_id}/messages',
    response_model=DocumentMessageList,
)
async def list_document_messages(
    doc_id: UUID,
    session: Session,
    filters: Annotated[MessageFilter, Depends()],
):
    messages = await message_service.list_messages(session, doc_id, filters)
    return {'messages': messages}


@router.get(
    '/message/{message_id}',
    response_model=DocumentMessagePublic,
)
async def read_document_message(message_id: UUID, session: Session):
    return await message_service.get_message_by_id(session, message_id)


@router.put(
    '/message',
    response_model=DocumentMessagePublic,
)
async def update_document_message(
    msg: DocumentMessageUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await message_service.update_message(session, current_user.id, msg)


@router.delete(
    '/message/{message_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_document_message(
    message_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await message_service.delete_message(session, current_user.id, message_id)
    return {'message': 'Message deleted successfully.'}


async def broadcast_event(
    socket_manager: WebSocketManager, channel_id: str, event: str, message: str
) -> None:
    ws_message = WSMessage(event=event, message=message, payload={})
    await socket_manager.broadcast_to_channel(
        channel_id, ws_message.model_dump_json()
    )


async def process_user_message(
    data: str,
    session: Session,
    user_id: UUID,
    doc_id: UUID,
    model: Model,
    vstore: VStore,
    socket_manager: WebSocketManager,
    channel_id: str,
) -> None:
    if not data or data == '\n':
        return

    msg = DocumentMessageCreate(content=data, mentions=[], quoted_message=None)
    await message_service.create_message(session, user_id, doc_id, msg)

    if message_service.requires_ai_response(data):
        filters = MessageFilter(limit=10)
        recent_messages = await message_service.list_messages(
            session, doc_id, filters
        )

        response = await ai_service.create_ai_response(
            session, user_id, doc_id, msg, model, vstore, recent_messages
        )

        ai_msg_create = DocumentMessageCreate(
            content=response['answer'],
            mentions=[MessageMention(id=doc_id, type=MessageEntityType.AI, label='OiacIA')],
            quoted_message=None,
        )
        await message_service.create_message(
            session, user_id, doc_id, ai_msg_create
        )

        ws_payload = {
            'answer': response['answer'],
            'references': response['references'],
        }
        await broadcast_event(
            socket_manager, channel_id, 'chat.ai.message', ws_payload
        )


@router.websocket('/message/{doc_id}/ws')
async def document_chat_websocket(
    websocket: WebSocket,
    doc_id: UUID,
    session: Session,
    model: Model,
    vstore: VStore,
    access_token: str | None = Cookie(default=None),
    socket_manager: WebSocketManager = Depends(get_socket_manager),
):
    current_user = await get_current_user(None, access_token, session)
    channel_id = f'ws:doc:{doc_id}:chat'

    await socket_manager.add_user_to_channel(channel_id, websocket)
    await broadcast_event(
        socket_manager,
        channel_id,
        'user.connect',
        f'User connected to channel - {channel_id}',
    )

    try:
        while True:
            data = await websocket.receive_text()
            await broadcast_event(
                socket_manager, channel_id, 'chat.message', data
            )
            await process_user_message(
                data=data,
                session=session,
                user_id=current_user.id,
                doc_id=doc_id,
                model=model,
                vstore=vstore,
                socket_manager=socket_manager,
                channel_id=channel_id,
            )
    except (WebSocketDisconnect, HTTPException) as exc:
        print('ERRO -> ', exc)
    finally:
        await socket_manager.remove_user_from_channel(channel_id, websocket)
        await broadcast_event(
            socket_manager,
            channel_id,
            'user.disconnect',
            f'User disconnected to channel - {channel_id}',
        )
