from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Branch
from iaEditais.repositories import branch_repo
from iaEditais.schemas import (
    BranchCreate,
    BranchFilter,
    BranchPublic,
    BranchUpdate,
)
from iaEditais.services import audit_service


async def create_branch(
    session: AsyncSession, user_id: UUID, data: BranchCreate
) -> Branch:
    # Verifica duplicidade
    existing_branch = await branch_repo.get_by_title_and_taxonomy(
        session, data.title, data.taxonomy_id
    )
    if existing_branch:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Branch title already exists for this taxonomy',
        )

    # Verifica taxonomia
    taxonomy = await branch_repo.get_taxonomy(session, data.taxonomy_id)
    if not taxonomy or taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    db_branch = Branch(
        title=data.title,
        description=data.description,
        taxonomy_id=data.taxonomy_id,
    )
    db_branch.set_creation_audit(user_id)

    branch_repo.add(session, db_branch)
    await session.flush()

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Branch.__tablename__,
        record_id=db_branch.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_branch)
    return db_branch


async def get_branches(
    session: AsyncSession, filters: BranchFilter
) -> list[Branch]:
    return await branch_repo.list_all(session, filters)


async def get_branch_by_id(session: AsyncSession, branch_id: UUID) -> Branch:
    branch = await branch_repo.get_by_id(session, branch_id)
    if not branch or branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )
    return branch


async def update_branch(
    session: AsyncSession, user_id: UUID, data: BranchUpdate
) -> Branch:
    db_branch = await branch_repo.get_by_id(session, data.id)

    if not db_branch or db_branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    old_data = BranchPublic.model_validate(db_branch).model_dump(mode='json')

    title_changed = data.title != db_branch.title
    taxonomy_changed = data.taxonomy_id != db_branch.taxonomy_id

    if title_changed or taxonomy_changed:
        conflict = await branch_repo.get_by_title_and_taxonomy(
            session, data.title, data.taxonomy_id, exclude_id=data.id
        )
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Branch title already exists for this taxonomy',
            )

    if taxonomy_changed:
        taxonomy = await branch_repo.get_taxonomy(session, data.taxonomy_id)
        if not taxonomy or taxonomy.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Taxonomy not found',
            )

    db_branch.title = data.title
    db_branch.description = data.description
    db_branch.taxonomy_id = data.taxonomy_id

    new_data = BranchPublic.model_validate(db_branch).model_dump(mode='json')
    db_branch.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Branch.__tablename__,
        record_id=db_branch.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_branch)
    return db_branch


async def delete_branch(
    session: AsyncSession, user_id: UUID, branch_id: UUID
) -> None:
    db_branch = await branch_repo.get_by_id(session, branch_id)

    if not db_branch or db_branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    old_data = BranchPublic.model_validate(db_branch).model_dump(mode='json')
    db_branch.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Branch.__tablename__,
        record_id=db_branch.id,
        old_data=old_data,
    )

    await session.commit()
