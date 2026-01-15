from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Branch, Taxonomy
from iaEditais.schemas import (
    BranchCreate,
    BranchFilter,
    BranchList,
    BranchPublic,
    BranchUpdate,
)
from iaEditais.services import audit

router = APIRouter(
    prefix='/branch',
    tags=['árvore de verificação, branches'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=BranchPublic,
)
async def create_branch(
    branch: BranchCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_branch = await session.scalar(
        select(Branch).where(
            Branch.deleted_at.is_(None),
            Branch.title == branch.title,
        )
    )

    if db_branch:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Branch title already exists',
        )

    taxonomy = await session.get(Taxonomy, branch.taxonomy_id)
    if not taxonomy or taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    # 1. Criação do objeto (AuditMixin trata created_by)
    db_branch = Branch(
        title=branch.title,
        description=branch.description,
        taxonomy_id=branch.taxonomy_id,
    )
    # 2. Preenche created_at e created_by via Mixin
    db_branch.set_creation_audit(current_user.id)

    session.add(db_branch)
    # Flush para garantir ID antes do log
    await session.flush()

    # 3. Registro de Auditoria (CREATE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Branch.__tablename__,
        record_id=db_branch.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_branch)

    return db_branch


@router.get('/', response_model=BranchList)
async def read_branches(
    session: Session, filters: Annotated[BranchFilter, Depends()]
):
    query = (
        select(Branch)
        .where(Branch.deleted_at.is_(None))
        .order_by(Branch.created_at.desc())
    )

    if filters.taxonomy_id:
        query = query.where(Branch.taxonomy_id == filters.taxonomy_id)

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    branches = result.all()

    return {'branches': branches}


@router.get('/{branch_id}', response_model=BranchPublic)
async def read_branch(branch_id: UUID, session: Session):
    result = await session.execute(
        select(Branch).where(Branch.id == branch_id)
    )
    branch = result.scalar_one_or_none()

    if not branch or branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    return branch


@router.put('/', response_model=BranchPublic)
async def update_branch(
    branch: BranchUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_branch = await session.get(Branch, branch.id)

    if not db_branch or db_branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    # 4. Snapshot antes da atualização
    old_data = BranchPublic.model_validate(db_branch).model_dump(mode='json')

    if branch.title != db_branch.title:
        db_branch_same_title = await session.scalar(
            select(Branch).where(
                Branch.deleted_at.is_(None),
                Branch.title == branch.title,
                Branch.id != branch.id,
            )
        )
        if db_branch_same_title:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Branch title already exists',
            )

    if branch.taxonomy_id != db_branch.taxonomy_id:
        taxonomy = await session.get(Taxonomy, branch.taxonomy_id)
        if not taxonomy or taxonomy.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Taxonomy not found',
            )

    db_branch.title = branch.title
    db_branch.description = branch.description
    db_branch.taxonomy_id = branch.taxonomy_id

    # 5. Preenche updated_at e updated_by via Mixin
    db_branch.set_update_audit(current_user.id)

    # 6. Registro de Auditoria (UPDATE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Branch.__tablename__,
        record_id=db_branch.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(db_branch)
    return db_branch


@router.delete(
    '/{branch_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_branch(
    branch_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_branch = await session.get(Branch, branch_id)

    if not db_branch or db_branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    # 7. Snapshot antes de deletar
    old_data = BranchPublic.model_validate(db_branch).model_dump(mode='json')

    # 8. Soft delete via Mixin
    db_branch.set_deletion_audit(current_user.id)

    # 9. Registro de Auditoria (DELETE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Branch.__tablename__,
        record_id=db_branch.id,
        old_data=old_data,
    )

    await session.commit()

    return {'message': 'Branch deleted'}
