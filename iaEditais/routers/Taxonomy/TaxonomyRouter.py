from fastapi import APIRouter
from http import HTTPStatus
from uuid import UUID
from iaEditais.schemas.Taxonomy import CreateTaxonomy, Taxonomy
from iaEditais.services import TaxonomyService

router = APIRouter()


@router.post(
    '/taxonomy/',
    status_code=HTTPStatus.CREATED,
    response_model=Taxonomy,
)
def post_taxonomy(taxonomy: CreateTaxonomy):
    return TaxonomyService.post_taxonomy(taxonomy)


@router.get(
    '/taxonomy/',
    status_code=HTTPStatus.OK,
    response_model=list[Taxonomy],
)
def get_taxonomy():
    return TaxonomyService.get_taxonomy()


@router.get(
    '/taxonomy/{typification_id}/',
    status_code=HTTPStatus.OK,
    response_model=list[Taxonomy],
)
def get_taxonomy_by_typification(typification_id: UUID):
    return TaxonomyService.get_taxonomy(typification_id)


@router.put(
    '/taxonomy/',
    status_code=HTTPStatus.OK,
    response_model=Taxonomy,
)
def put_taxonomy(taxonomy: Taxonomy):
    return TaxonomyService.put_taxonomy(taxonomy)


@router.delete('/taxonomy/{taxonomy_id}/', status_code=HTTPStatus.NO_CONTENT)
def delete_taxonomy(taxonomy_id: UUID):
    return TaxonomyService.delete_taxonomy(taxonomy_id)
