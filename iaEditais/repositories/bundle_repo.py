from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import (
    Bundle,
    BundleDocument,
    BundleDocumentTypification,
    Typification,
)
from iaEditais.repositories import util
from iaEditais.schemas.bundle import BundleFilter


async def get_by_id(
    session: AsyncSession, bundle_id: UUID
) -> Optional[Bundle]:
    return await session.get(Bundle, bundle_id)


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: UUID = None
) -> Optional[Bundle]:
    stmt = select(Bundle).where(
        Bundle.deleted_at.is_(None), Bundle.name == name
    )
    if exclude_id:
        stmt = stmt.where(Bundle.id != exclude_id)
    return await session.scalar(stmt)


async def get_document_by_id(
    session: AsyncSession, document_id: UUID
) -> Optional[BundleDocument]:
    return await session.get(BundleDocument, document_id)


async def get_typifications_by_ids(
    session: AsyncSession, typification_ids: list[UUID]
) -> Sequence[Typification]:
    if not typification_ids:
        return []
    stmt = select(Typification).where(Typification.id.in_(typification_ids))
    result = await session.scalars(stmt)
    return result.all()


async def list_all(
    session: AsyncSession, filters: BundleFilter
) -> list[Bundle]:
    query = select(Bundle).order_by(Bundle.created_at.desc())

    if filters.q:
        query = util.apply_text_search(query, Bundle, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add_bundle(session: AsyncSession, bundle: Bundle) -> None:
    session.add(bundle)


def add_bundle_document(
    session: AsyncSession, document: BundleDocument
) -> None:
    session.add(document)


def add_bundle_document_typification(
    session: AsyncSession, association: BundleDocumentTypification
) -> None:
    session.add(association)


async def get_bundle_with_relations(
    session: AsyncSession, bundle_id: UUID
) -> Bundle | None:
    stmt = (
        select(Bundle)
        .where(Bundle.id == bundle_id)
        .options(
            selectinload(Bundle.documents).selectinload(
                BundleDocument.typifications
            )
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
