from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.schemas.branch import Branch, CreateBranch
from iaEditais.services import taxonomy_service

router = APIRouter()


@router.post(
    '/taxonomy/branch/',
    response_model=Branch,
    status_code=HTTPStatus.CREATED,
)
async def post_branch(
    branch: CreateBranch, conn: Connection = Depends(get_conn)
):
    return await taxonomy_service.post_branch(conn, branch)


@router.get('/taxonomy/branch/{taxonomy_id}/', response_model=list[Branch])
async def get_branch_by_taxonomy(
    taxonomy_id: UUID, conn: Connection = Depends(get_conn)
):
    return await taxonomy_service.get_branches(conn, taxonomy_id)


@router.put('/taxonomy/branch/', response_model=Branch)
async def put_branch(branch: Branch, conn: Connection = Depends(get_conn)):
    return await taxonomy_service.put_branch(conn, branch)


@router.delete(
    '/taxonomy/branch/{branch_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_branch(branch_id: UUID, conn: Connection = Depends(get_conn)):
    return await taxonomy_service.delete_branch(conn, branch_id)
