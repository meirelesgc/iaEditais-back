from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import (
    AppliedTaxonomy,
    AppliedTypification,
    Branch,
    Document,
    DocumentHistory,
    DocumentRelease,
    Taxonomy,
    Typification,
)


async def get_release_with_details(
    session: AsyncSession, release_id: UUID
) -> Optional[DocumentRelease]:
    stmt = (
        select(DocumentRelease)
        .where(DocumentRelease.id == release_id)
        .options(
            selectinload(DocumentRelease.history)
            .selectinload(DocumentHistory.document)
            .selectinload(Document.editors)
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_full_branch(
    session: AsyncSession, branch_id: UUID
) -> Optional[Branch]:
    stmt = (
        select(Branch)
        .where(Branch.id == branch_id)
        .options(
            selectinload(Branch.taxonomy).selectinload(Taxonomy.sources),
            selectinload(Branch.taxonomy)
            .selectinload(Taxonomy.typification)
            .selectinload(Typification.sources),
        )
    )
    return await session.scalar(stmt)


async def get_applied_typification(
    session: AsyncSession, original_id: UUID, release_id: UUID
) -> Optional[AppliedTypification]:
    stmt = select(AppliedTypification).where(
        AppliedTypification.original_id == original_id,
        AppliedTypification.applied_release_id == release_id,
    )
    return await session.scalar(stmt)


async def get_applied_taxonomy(
    session: AsyncSession, original_id: UUID, typification_id: UUID
) -> Optional[AppliedTaxonomy]:
    stmt = select(AppliedTaxonomy).where(
        AppliedTaxonomy.original_id == original_id,
        AppliedTaxonomy.applied_typification_id == typification_id,
    )
    return await session.scalar(stmt)


def add_applied_entity(session: AsyncSession, entity) -> None:
    session.add(entity)


def add_document(session: AsyncSession, doc: Document) -> None:
    session.add(doc)
