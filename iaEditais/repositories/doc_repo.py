from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from iaEditais.models import Document, DocumentHistory, Typification, User
from iaEditais.repositories import util
from iaEditais.schemas import DocumentFilter


async def get_by_id(session: AsyncSession, doc_id: UUID) -> Optional[Document]:
    stmt = select(Document).where(Document.id == doc_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_identifier(
    session: AsyncSession, identifier: str, exclude_id: UUID = None
) -> Optional[Document]:
    stmt = select(Document).where(Document.identifier == identifier)
    if exclude_id:
        stmt = stmt.where(Document.id != exclude_id)
    return await session.scalar(stmt)


async def list_all(
    session: AsyncSession, filters: DocumentFilter
) -> list[Document]:
    # Lógica de Lateral Join para pegar o último histórico
    last_history_subq = (
        select(DocumentHistory)
        .where(DocumentHistory.document_id == Document.id)
        .order_by(DocumentHistory.created_at.desc())
        .limit(1)
        .lateral()
    )

    last_history = aliased(DocumentHistory, last_history_subq)

    query = (
        select(Document)
        .join(last_history, true())
        .where(
            Document.deleted_at.is_(None),
            Document.is_test == False,  # noqa: E712
        )
        .order_by(last_history.status.asc(), last_history.created_at.asc())
    )

    if filters.unit_id:
        query = query.where(Document.unit_id == filters.unit_id)

    if filters.archived is not None:
        query = query.where(Document.is_archived == filters.archived)

    if filters.q:
        query = util.apply_text_search(query, Document, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    return result.all()


async def get_typifications_by_ids(
    session: AsyncSession, ids: list[UUID]
) -> Sequence[Typification]:
    if not ids:
        return []
    stmt = select(Typification).where(Typification.id.in_(ids))
    result = await session.scalars(stmt)
    return result.all()


async def get_users_by_ids(
    session: AsyncSession, ids: list[UUID]
) -> Sequence[User]:
    if not ids:
        return []
    stmt = select(User).where(User.id.in_(ids))
    result = await session.scalars(stmt)
    return result.all()


def add_document(session: AsyncSession, doc: Document) -> None:
    session.add(doc)


def add_history(session: AsyncSession, history: DocumentHistory) -> None:
    session.add(history)
