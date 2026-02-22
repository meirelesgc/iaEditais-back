from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    DocumentMessageCreate,
    DocumentMessageList,
    DocumentMessagePublic,
    DocumentMessageUpdate,
)
from iaEditais.schemas.document_message import MessageFilter
from iaEditais.services import message_service

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
