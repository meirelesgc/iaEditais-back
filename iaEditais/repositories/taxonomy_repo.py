from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Source, Taxonomy, TaxonomySource, Typification
from iaEditais.repositories import util
from iaEditais.schemas.taxonomy import TaxonomyFilter


async def get_by_id(
    session: AsyncSession, taxonomy_id: UUID
) -> Optional[Taxonomy]:
    stmt = select(Taxonomy).where(Taxonomy.id == taxonomy_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_conflict(
    session: AsyncSession,
    title: str,
    typification_id: UUID,
    exclude_id: UUID = None,
) -> Optional[Taxonomy]:
    stmt = select(Taxonomy).where(
        Taxonomy.title == title,
        Taxonomy.typification_id == typification_id,
    )
    if exclude_id:
        stmt = stmt.where(Taxonomy.id != exclude_id)
    return await session.scalar(stmt)


async def get_typification(
    session: AsyncSession, typification_id: UUID
) -> Optional[Typification]:
    return await session.get(Typification, typification_id)


async def get_sources_by_ids(
    session: AsyncSession, source_ids: list[UUID]
) -> Sequence[Source]:
    if not source_ids:
        return []
    stmt = select(Source).where(Source.id.in_(source_ids))
    result = await session.scalars(stmt)
    return result.all()


async def list_all(
    session: AsyncSession, filters: TaxonomyFilter
) -> list[Taxonomy]:
    query = select(Taxonomy).order_by(Taxonomy.created_at.desc())

    if filters.typification_id:
        query = query.where(
            Taxonomy.typification_id == filters.typification_id
        )

    if filters.q:
        query = util.apply_text_search(query, Taxonomy, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add_taxonomy(session: AsyncSession, taxonomy: Taxonomy) -> None:
    session.add(taxonomy)


def add_taxonomy_source(
    session: AsyncSession, association: TaxonomySource
) -> None:
    session.add(association)
