from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import (
    Document,
    DocumentMessage,
    DocumentMessageMention,
    DocumentRelease,
)
from iaEditais.schemas import (
    DocumentMessageCreate,
    DocumentMessageList,
    DocumentMessagePublic,
    DocumentMessageUpdate,
)
from iaEditais.schemas.document_message import MessageFilter

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
    document = await session.get(Document, doc_id)
    if not document or document.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found.',
        )

    latest_release = await session.scalar(
        select(DocumentRelease)
        .where(DocumentRelease.history.has(document_id=doc_id))
        .order_by(DocumentRelease.created_at.desc())
    )

    db_msg = DocumentMessage(
        content=msg.content,
        document_id=doc_id,
        release_id=latest_release.id if latest_release else None,
        author_id=current_user.id,
        created_by=current_user.id,
    )

    if msg.quoted_message:
        db_msg.quoted_message_id = msg.quoted_message.id

    session.add(db_msg)
    await session.flush()

    if msg.mentions:
        mentions = [
            DocumentMessageMention(
                message_id=db_msg.id,
                entity_id=mention.id,
                entity_type=mention.type.value,
                label=mention.label,
            )
            for mention in msg.mentions
        ]
        session.add_all(mentions)

    await session.commit()
    await session.refresh(db_msg)
    return db_msg


@router.get(
    '/{doc_id}/messages',
    response_model=DocumentMessageList,
)
async def list_document_messages(
    doc_id: UUID,
    session: Session,
    filters: Annotated[MessageFilter, Depends()],
):
    document = await session.get(Document, doc_id)
    if not document or document.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found.',
        )

    query = (
        select(DocumentMessage)
        .where(
            DocumentMessage.document_id == doc_id,
            DocumentMessage.deleted_at.is_(None),
        )
        .order_by(DocumentMessage.created_at.desc())
    )

    if filters.author_id:
        query = query.where(DocumentMessage.author_id == filters.author_id)

    if filters.release_id:
        query = query.where(DocumentMessage.release_id == filters.release_id)

    if filters.start_date and filters.end_date:
        query = query.where(
            and_(
                DocumentMessage.created_at >= filters.start_date,
                DocumentMessage.created_at <= filters.end_date,
            )
        )
    if filters.mention_id or filters.mention_type:
        query = query.join(DocumentMessage.mentions)
        if filters.mention_id:
            query = query.where(
                DocumentMessageMention.entity_id == filters.mention_id
            )
        if filters.mention_type:
            query = query.where(
                DocumentMessageMention.entity_type == filters.mention_type
            )

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    messages = result.all()

    return {'messages': messages}


@router.get(
    '/message/{message_id}',
    response_model=DocumentMessagePublic,
)
async def read_document_message(message_id: UUID, session: Session):
    msg = await session.get(DocumentMessage, message_id)
    if not msg or msg.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Message not found.',
        )
    return msg


@router.put(
    '/message',
    response_model=DocumentMessagePublic,
)
async def update_document_message(
    msg: DocumentMessageUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_msg = await session.get(DocumentMessage, msg.id)
    if not db_msg or db_msg.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Message not found.',
        )

    db_msg.content = msg.content
    db_msg.updated_by = current_user.id
    db_msg.updated_at = datetime.now(timezone.utc)

    await session.execute(
        delete(DocumentMessageMention).where(
            DocumentMessageMention.message_id == db_msg.id
        )
    )

    if msg.mentions:
        mentions = [
            DocumentMessageMention(
                message_id=db_msg.id,
                entity_id=mention.id,
                entity_type=mention.type.value,
                label=mention.label,
            )
            for mention in msg.mentions
        ]
        session.add_all(mentions)

    await session.commit()
    await session.refresh(db_msg)
    return db_msg


@router.delete(
    '/message/{message_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_document_message(
    message_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_msg = await session.get(DocumentMessage, message_id)
    if not db_msg or db_msg.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Message not found.',
        )

    db_msg.deleted_at = datetime.now(timezone.utc)
    db_msg.deleted_by = current_user.id
    await session.commit()

    return {'message': 'Message deleted successfully.'}
