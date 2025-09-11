from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Branch, Taxonomy
from iaEditais.schemas import (
    BranchCreate,
    BranchList,
    BranchPublic,
    BranchUpdate,
    FilterPage,
    Message,
)

router = APIRouter(
    prefix='/branch',
    tags=['árvore de verificação, branches'],
)


Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=BranchPublic,
)
async def create_branch(branch: BranchCreate, session: Session):
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

    db_branch = Branch(
        title=branch.title,
        description=branch.description,
        taxonomy_id=branch.taxonomy_id,
    )

    session.add(db_branch)
    await session.commit()
    await session.refresh(db_branch, attribute_names=['taxonomy'])

    return db_branch


@router.get('/', response_model=BranchList)
async def read_branches(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Branch)
        .where(Branch.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )
    branches = query.all()
    return {'branches': branches}


@router.get('/{branch_id}', response_model=BranchPublic)
async def read_branch(branch_id: UUID, session: Session):
    branch = await session.get(Branch, branch_id)

    if not branch or branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    return branch


@router.put('/', response_model=BranchPublic)
async def update_branch(branch: BranchUpdate, session: Session):
    db_branch = await session.get(Branch, branch.id)

    if not db_branch or db_branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

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

    try:
        await session.commit()
        await session.refresh(
            db_branch, attribute_names=['taxonomy', 'updated_at']
        )
        return db_branch
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Branch title already exists',
        )


@router.delete('/{branch_id}', response_model=Message)
async def delete_branch(branch_id: UUID, session: Session):
    db_branch = await session.get(Branch, branch_id)

    if not db_branch or db_branch.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Branch not found',
        )

    db_branch.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    return {'message': 'Branch deleted'}
