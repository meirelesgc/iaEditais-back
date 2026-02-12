from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Unit
from iaEditais.repositories import util
from iaEditais.schemas import UnitFilter


async def get_by_id(session: AsyncSession, unit_id: UUID) -> Optional[Unit]:
    stmt = select(Unit).where(Unit.id == unit_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: UUID = None
) -> Optional[Unit]:
    stmt = select(Unit).where(Unit.deleted_at.is_(None), Unit.name == name)
    if exclude_id:
        stmt = stmt.where(Unit.id != exclude_id)
    return await session.scalar(stmt)


async def list_all(session: AsyncSession, filters: UnitFilter) -> list[Unit]:
    query = select(Unit).order_by(Unit.created_at.desc())

    if filters.q:
        query = util.apply_text_search(query, Unit, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add(session: AsyncSession, unit: Unit) -> None:
    session.add(unit)
