from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    BranchCreate,
    BranchFilter,
    BranchList,
    BranchPublic,
    BranchUpdate,
)
from iaEditais.services import branch_service

router = APIRouter(
    prefix='/branch',
    tags=['árvore de verificação, branches'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=BranchPublic,
)
async def create_branch(
    branch: BranchCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await branch_service.create_branch(session, current_user.id, branch)


@router.get('', response_model=BranchList)
async def read_branches(
    session: Session, filters: Annotated[BranchFilter, Depends()]
):
    branches = await branch_service.get_branches(session, filters)
    return {'branches': branches}


@router.get('/{branch_id}', response_model=BranchPublic)
async def read_branch(branch_id: UUID, session: Session):
    return await branch_service.get_branch_by_id(session, branch_id)


@router.put('', response_model=BranchPublic)
async def update_branch(
    branch: BranchUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await branch_service.update_branch(session, current_user.id, branch)


@router.delete(
    '/{branch_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_branch(
    branch_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await branch_service.delete_branch(session, current_user.id, branch_id)
    return {'message': 'Branch deleted'}
