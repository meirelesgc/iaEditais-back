from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Source, Typification, TypificationSource
from iaEditais.repositories import util
from iaEditais.schemas import TypificationFilter


async def get_by_id(
    session: AsyncSession, typification_id: UUID
) -> Optional[Typification]:
    return await session.get(Typification, typification_id)


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: UUID = None
) -> Optional[Typification]:
    stmt = select(Typification).where(
        Typification.deleted_at.is_(None), Typification.name == name
    )
    if exclude_id:
        stmt = stmt.where(Typification.id != exclude_id)
    return await session.scalar(stmt)


async def get_sources_by_ids(
    session: AsyncSession, source_ids: list[UUID]
) -> Sequence[Source]:
    if not source_ids:
        return []
    stmt = select(Source).where(Source.id.in_(source_ids))
    result = await session.scalars(stmt)
    return result.all()


async def list_all(
    session: AsyncSession, filters: TypificationFilter
) -> list[Typification]:
    query = select(Typification).order_by(Typification.created_at.desc())

    if filters.q:
        query = util.apply_text_search(query, Typification, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


async def list_for_report(
    session: AsyncSession, typification_id: UUID = None
) -> list[Typification]:
    stmt = (
        select(Typification)
        .where(Typification.deleted_at.is_(None))
        .order_by(Typification.created_at.desc())
    )

    if typification_id:
        stmt = stmt.where(Typification.id == typification_id)

    query = await session.scalars(stmt)
    return query.all()


def add_typification(
    session: AsyncSession, typification: Typification
) -> None:
    session.add(typification)


def add_typification_source(
    session: AsyncSession, association: TypificationSource
) -> None:
    session.add(association)
