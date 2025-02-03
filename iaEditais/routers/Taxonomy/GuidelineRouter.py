from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.Guideline import CreateGuideline, Guideline
from iaEditais.services import TaxonomyService

router = APIRouter()


@router.post('/taxonomy/guidelines/')
def post_guideline(guideline: CreateGuideline) -> Guideline:
    return TaxonomyService.post_guideline(guideline)


@router.get('/taxonomy/guidelines/', response_model=list[Guideline])
def get_guideline():
    return TaxonomyService.get_guidelines()


@router.put('/taxonomy/guidelines/', response_model=Guideline)
def put_guideline(guideline: Guideline):
    return TaxonomyService.put_guideline(guideline)


@router.delete('/taxonomy/guidelines/{guideline_id}/')
def delete_guideline(guideline_id: UUID):
    return TaxonomyService.delete_guideline(guideline_id)
