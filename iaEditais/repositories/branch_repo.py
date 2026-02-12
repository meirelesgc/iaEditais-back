from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Branch, Taxonomy
from iaEditais.repositories import util
from iaEditais.schemas import BranchFilter


async def get_by_id(
    session: AsyncSession, branch_id: UUID
) -> Optional[Branch]:
    stmt = select(Branch).where(Branch.id == branch_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_title_and_taxonomy(
    session: AsyncSession,
    title: str,
    taxonomy_id: UUID,
    exclude_id: UUID = None,
) -> Optional[Branch]:
    stmt = select(Branch).where(
        Branch.title == title, Branch.taxonomy_id == taxonomy_id
    )
    if exclude_id:
        stmt = stmt.where(Branch.id != exclude_id)

    return await session.scalar(stmt)


async def get_taxonomy(
    session: AsyncSession, taxonomy_id: UUID
) -> Optional[Taxonomy]:
    return await session.get(Taxonomy, taxonomy_id)


async def list_all(
    session: AsyncSession, filters: BranchFilter
) -> list[Branch]:
    query = select(Branch).order_by(Branch.created_at.desc())

    if filters.taxonomy_id:
        query = query.where(Branch.taxonomy_id == filters.taxonomy_id)

    if filters.q:
        query = util.apply_text_search(query, Branch, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add(session: AsyncSession, branch: Branch) -> None:
    session.add(branch)
