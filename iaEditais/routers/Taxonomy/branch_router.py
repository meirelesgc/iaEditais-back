from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.branch import CreateBranch, Branch
from iaEditais.services import taxonomy_service
from http import HTTPStatus

router = APIRouter()


@router.post(
    '/taxonomy/branch/',
    response_model=Branch,
    status_code=HTTPStatus.CREATED,
)
def post_branch(branch: CreateBranch):
    return taxonomy_service.post_branch(branch)


@router.get('/taxonomy/branch/{taxonomy_id}/', response_model=list[Branch])
def get_branch_by_taxonomy(taxonomy_id: UUID):
    return taxonomy_service.get_branches(taxonomy_id)


@router.put('/taxonomy/branch/', response_model=Branch)
def put_branch(branch: Branch):
    return taxonomy_service.put_branch(branch)


@router.delete(
    '/taxonomy/branch/{branch_id}/', status_code=HTTPStatus.NO_CONTENT
)
def delete_branch(branch_id: UUID):
    return taxonomy_service.delete_branch(branch_id)
