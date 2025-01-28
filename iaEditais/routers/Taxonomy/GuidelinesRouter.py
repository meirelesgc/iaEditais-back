from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.Guideline import CreateGuideline, Guideline
from iaEditais.services import TaxonomyService

router = APIRouter()


@router.post('/taxonomy/guidelines/')
def post_guideline(guideline: CreateGuideline) -> Guideline:
    return TaxonomyService.post_guideline(guideline)


@router.get(
    '/taxonomy/guidelines/{guideline_id}/',
    response_model=Guideline | list[Guideline],
)
def get_guideline(guideline_id: UUID = None):
    return TaxonomyService.get_guidelines(guideline_id)


@router.put('/taxonomy/guidelines/')
def put_guideline(guideline: Guideline) -> Guideline:
    return TaxonomyService.put_guideline(guideline)


@router.delete('/taxonomy/guidelines/{guideline_id}/')
def delete_guideline(guideline_id: UUID):
    return TaxonomyService.delete_guideline(guideline_id)
