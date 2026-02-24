from datetime import datetime, timezone
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import DocumentMessage, DocumentMessageMention
from iaEditais.repositories import message_repo
from iaEditais.schemas import (
    DocumentMessageCreate,
    DocumentMessageUpdate,
)
from iaEditais.schemas.document_message import MessageFilter


async def create_message(
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    data: DocumentMessageCreate,
) -> DocumentMessage:
    document = await message_repo.get_document(session, doc_id)
    if not document or document.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found.',
        )

    latest_release = await message_repo.get_latest_release(session, doc_id)

    db_msg = DocumentMessage(
        content=data.content,
        document_id=doc_id,
        release_id=latest_release.id if latest_release else None,
        author_id=user_id,
        created_by=user_id,
    )

    if data.quoted_message:
        db_msg.quoted_message_id = data.quoted_message.id

    message_repo.add_message(session, db_msg)
    await session.flush()

    if data.mentions:
        mentions = [
            DocumentMessageMention(
                message_id=db_msg.id,
                entity_id=mention.id,
                entity_type=mention.type.value,
                label=mention.label,
            )
            for mention in data.mentions
        ]
        message_repo.add_mentions(session, mentions)

    await session.commit()
    await session.refresh(db_msg)
    return db_msg


async def list_messages(
    session: AsyncSession, doc_id: UUID, filters: MessageFilter
) -> list[DocumentMessage]:
    document = await message_repo.get_document(session, doc_id)
    if not document or document.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found.',
        )
    return await message_repo.list_messages(session, doc_id, filters)


async def get_message_by_id(
    session: AsyncSession, message_id: UUID
) -> DocumentMessage:
    msg = await message_repo.get_message(session, message_id)
    if not msg or msg.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Message not found.',
        )
    return msg


async def update_message(
    session: AsyncSession, user_id: UUID, data: DocumentMessageUpdate
) -> DocumentMessage:
    db_msg = await get_message_by_id(session, data.id)

    db_msg.content = data.content
    db_msg.updated_by = user_id
    db_msg.updated_at = datetime.now(timezone.utc)

    # Limpa menções antigas
    await message_repo.delete_mentions_by_message(session, db_msg.id)

    # Adiciona novas menções
    if data.mentions:
        mentions = [
            DocumentMessageMention(
                message_id=db_msg.id,
                entity_id=mention.id,
                entity_type=mention.type.value,
                label=mention.label,
            )
            for mention in data.mentions
        ]
        message_repo.add_mentions(session, mentions)

    await session.commit()
    await session.refresh(db_msg)
    return db_msg


async def delete_message(
    session: AsyncSession, user_id: UUID, message_id: UUID
) -> None:
    db_msg = await get_message_by_id(session, message_id)

    db_msg.deleted_at = datetime.now(timezone.utc)
    db_msg.deleted_by = user_id
    await session.commit()
