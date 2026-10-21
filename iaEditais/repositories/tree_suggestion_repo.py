from datetime import datetime
from typing import Iterable, Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import TreeSuggestionItem, TreeSuggestionSession
from iaEditais.schemas.tree_suggestion import (
    TreeSuggestionFilter,
    TreeSuggestionItemStatus,
)


def add_session(
    session: AsyncSession, suggestion_session: TreeSuggestionSession
) -> None:
    session.add(suggestion_session)


def add_items(
    session: AsyncSession, items: Iterable[TreeSuggestionItem]
) -> None:
    session.add_all(list(items))


async def get_session(
    session: AsyncSession, session_id: UUID
) -> Optional[TreeSuggestionSession]:
    stmt = (
        select(TreeSuggestionSession)
        .options(selectinload(TreeSuggestionSession.items))
        .where(
            TreeSuggestionSession.id == session_id,
            TreeSuggestionSession.deleted_at.is_(None),
        )
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def list_sessions(
    session: AsyncSession, filters: TreeSuggestionFilter
) -> Sequence[TreeSuggestionSession]:
    stmt = select(TreeSuggestionSession).where(
        TreeSuggestionSession.deleted_at.is_(None)
    )
    if filters.status:
        stmt = stmt.where(TreeSuggestionSession.status == filters.status)
    stmt = (
        stmt.order_by(TreeSuggestionSession.created_at.desc())
        .offset(filters.offset)
        .limit(filters.limit)
    )
    result = await session.scalars(stmt)
    return result.all()


async def get_item_for_update(
    session: AsyncSession, session_id: UUID, item_id: UUID
) -> Optional[TreeSuggestionItem]:
    stmt = (
        select(TreeSuggestionItem)
        .where(
            TreeSuggestionItem.id == item_id,
            TreeSuggestionItem.session_id == session_id,
        )
        .with_for_update()
    )
    return await session.scalar(stmt)


async def get_item(
    session: AsyncSession, item_id: UUID
) -> Optional[TreeSuggestionItem]:
    return await session.get(TreeSuggestionItem, item_id)


async def list_pending_descendant_ids(
    session: AsyncSession, item_id: UUID
) -> list[UUID]:
    """IDs dos descendentes pendentes do item (sem incluir o próprio)."""
    tree = (
        select(TreeSuggestionItem.id)
        .where(TreeSuggestionItem.parent_item_id == item_id)
        .cte(name='descendants', recursive=True)
    )
    children = select(TreeSuggestionItem.id).where(
        TreeSuggestionItem.parent_item_id == tree.c.id
    )
    tree = tree.union_all(children)

    stmt = select(TreeSuggestionItem.id).where(
        TreeSuggestionItem.id.in_(select(tree.c.id)),
        TreeSuggestionItem.status == TreeSuggestionItemStatus.PENDING.value,
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def list_pending_ids(
    session: AsyncSession, session_id: UUID
) -> list[UUID]:
    stmt = select(TreeSuggestionItem.id).where(
        TreeSuggestionItem.session_id == session_id,
        TreeSuggestionItem.status == TreeSuggestionItemStatus.PENDING.value,
    )
    result = await session.scalars(stmt)
    return list(result.all())


async def count_pending(session: AsyncSession, session_id: UUID) -> int:
    stmt = select(func.count(TreeSuggestionItem.id)).where(
        TreeSuggestionItem.session_id == session_id,
        TreeSuggestionItem.status == TreeSuggestionItemStatus.PENDING.value,
    )
    return await session.scalar(stmt) or 0


async def mark_discarded(
    session: AsyncSession,
    item_ids: Sequence[UUID],
    user_id: UUID,
    reviewed_at: datetime,
) -> None:
    if not item_ids:
        return
    stmt = (
        update(TreeSuggestionItem)
        .where(
            TreeSuggestionItem.id.in_(item_ids),
            TreeSuggestionItem.status
            == TreeSuggestionItemStatus.PENDING.value,
        )
        .values(
            status=TreeSuggestionItemStatus.DISCARDED.value,
            reviewed_by=user_id,
            reviewed_at=reviewed_at,
        )
        .execution_options(synchronize_session='fetch')
    )
    await session.execute(stmt)


async def list_confirmed(
    session: AsyncSession, session_id: UUID, kinds: Sequence[str]
) -> Sequence[TreeSuggestionItem]:
    stmt = select(TreeSuggestionItem).where(
        TreeSuggestionItem.session_id == session_id,
        TreeSuggestionItem.status == TreeSuggestionItemStatus.CONFIRMED.value,
        TreeSuggestionItem.kind.in_(kinds),
    )
    result = await session.scalars(stmt)
    return result.all()
