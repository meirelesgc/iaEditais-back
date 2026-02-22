from typing import Optional
from uuid import UUID

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import (
    Document,
    DocumentMessage,
    DocumentMessageMention,
    DocumentRelease,
)
from iaEditais.schemas.document_message import MessageFilter


async def get_document(
    session: AsyncSession, doc_id: UUID
) -> Optional[Document]:
    return await session.get(Document, doc_id)


async def get_latest_release(
    session: AsyncSession, doc_id: UUID
) -> Optional[DocumentRelease]:
    stmt = (
        select(DocumentRelease)
        .where(DocumentRelease.history.has(document_id=doc_id))
        .order_by(DocumentRelease.created_at.desc())
    )
    return await session.scalar(stmt)


async def get_message(
    session: AsyncSession, message_id: UUID
) -> Optional[DocumentMessage]:
    return await session.get(DocumentMessage, message_id)


async def list_messages(
    session: AsyncSession, doc_id: UUID, filters: MessageFilter
) -> list[DocumentMessage]:
    query = (
        select(DocumentMessage)
        .where(DocumentMessage.document_id == doc_id)
        .order_by(DocumentMessage.created_at.desc())
        .execution_options(skip_soft_delete_filter=True)
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

    # Filtro por menções exige Join
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
    return result.all()


async def delete_mentions_by_message(
    session: AsyncSession, message_id: UUID
) -> None:
    await session.execute(
        delete(DocumentMessageMention).where(
            DocumentMessageMention.message_id == message_id
        )
    )


def add_message(session: AsyncSession, msg: DocumentMessage) -> None:
    session.add(msg)


def add_mentions(
    session: AsyncSession, mentions: list[DocumentMessageMention]
) -> None:
    session.add_all(mentions)
