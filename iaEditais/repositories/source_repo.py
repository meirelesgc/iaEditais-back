from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Source
from iaEditais.repositories import util
from iaEditais.schemas.source import SourceFilter


async def get_by_id(
    session: AsyncSession, source_id: UUID
) -> Optional[Source]:
    stmt = select(Source).where(Source.id == source_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: UUID = None
) -> Optional[Source]:
    stmt = select(Source).where(Source.name == name)
    if exclude_id:
        stmt = stmt.where(Source.id != exclude_id)
    return await session.scalar(stmt)


async def list_all(
    session: AsyncSession, filters: SourceFilter
) -> list[Source]:
    query = select(Source).order_by(Source.created_at.desc())

    if filters.q:
        query = util.apply_text_search(query, Source, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add(session: AsyncSession, source: Source) -> None:
    session.add(source)
