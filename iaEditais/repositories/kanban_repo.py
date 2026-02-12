from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import Document, DocumentHistory, User


async def get_with_editors(
    session: AsyncSession, doc_id: UUID
) -> Optional[Document]:
    stmt = (
        select(Document)
        .options(selectinload(Document.editors))
        .where(Document.id == doc_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user(session: AsyncSession, user_id: UUID) -> Optional[User]:
    return await session.get(User, user_id)


async def get_unit_auditors(
    session: AsyncSession, unit_id: UUID
) -> Sequence[User]:
    stmt = select(User).where(
        User.access_level == 'AUDITOR',
        User.unit_id == unit_id,
    )
    result = await session.execute(stmt)
    return result.scalars().all()


def add_history(session: AsyncSession, history: DocumentHistory) -> None:
    session.add(history)
