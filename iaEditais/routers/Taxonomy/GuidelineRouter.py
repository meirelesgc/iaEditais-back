from fastapi import APIRouter
from http import HTTPStatus
from uuid import UUID
from iaEditais.schemas.Guideline import CreateGuideline, Guideline
from iaEditais.services import TaxonomyService

router = APIRouter()


@router.post(
    '/taxonomy/guideline/',
    status_code=HTTPStatus.CREATED,
    response_model=Guideline,
)
def post_guideline(guideline: CreateGuideline):
    return TaxonomyService.post_guideline(guideline)


@router.get(
    '/taxonomy/guideline/',
    status_code=HTTPStatus.OK,
    response_model=list[Guideline],
)
def get_guideline():
    return TaxonomyService.get_guidelines()


@router.put(
    '/taxonomy/guideline/',
    status_code=HTTPStatus.OK,
    response_model=Guideline,
)
def put_guideline(guideline: Guideline):
    return TaxonomyService.put_guideline(guideline)


@router.delete(
    '/taxonomy/guideline/{guideline_id}/', status_code=HTTPStatus.NO_CONTENT
)
def delete_guideline(guideline_id: UUID):
    return TaxonomyService.delete_guideline(guideline_id)
