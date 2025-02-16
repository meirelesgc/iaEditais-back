from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.Branch import CreateBranch, Branch
from iaEditais.services import TaxonomyService
from http import HTTPStatus

router = APIRouter()


@router.post(
    '/taxonomy/branch/',
    response_model=Branch,
    status_code=HTTPStatus.CREATED,
)
def post_branch(branch: CreateBranch):
    return TaxonomyService.post_branch(branch)


@router.get('/taxonomy/branch/{taxonomy_id}/', response_model=list[Branch])
def get_branch_by_taxonomy(taxonomy_id: UUID):
    return TaxonomyService.get_branches(taxonomy_id)


@router.put('/taxonomy/branch/', response_model=Branch)
def put_branch(branch: Branch):
    return TaxonomyService.put_branch(branch)


@router.delete(
    '/taxonomy/branch/{branch_id}/', status_code=HTTPStatus.NO_CONTENT
)
def delete_branch(branch_id: UUID):
    return TaxonomyService.delete_branch(branch_id)
