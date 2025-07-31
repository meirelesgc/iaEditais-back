from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models.taxonomy_model import (
    CreateTaxonomy,
    Taxonomy,
    TaxonomyUpdate,
)
from iaEditais.services import taxonomy_service

router = APIRouter()


@router.post(
    '/taxonomy/',
    status_code=HTTPStatus.CREATED,
    response_model=Taxonomy,
)
async def post_taxonomy(
    taxonomy: CreateTaxonomy, conn: Connection = Depends(get_conn)
):
    return await taxonomy_service.post_taxonomy(conn, taxonomy)


@router.get(
    '/taxonomy/',
    status_code=HTTPStatus.OK,
    response_model=list[Taxonomy],
)
async def get_taxonomy(conn: Connection = Depends(get_conn)):
    return await taxonomy_service.get_taxonomy(conn)


@router.get(
    '/taxonomy/{typification_id}/',
    status_code=HTTPStatus.OK,
    response_model=list[Taxonomy],
)
async def get_taxonomy_by_typification(
    typification_id: UUID, conn: Connection = Depends(get_conn)
):
    return await taxonomy_service.get_taxonomy(conn, typification_id)


@router.put(
    '/taxonomy/',
    status_code=HTTPStatus.OK,
    response_model=Taxonomy,
)
async def put_taxonomy(
    taxonomy: TaxonomyUpdate, conn: Connection = Depends(get_conn)
):
    return await taxonomy_service.put_taxonomy(conn, taxonomy)


@router.delete('/taxonomy/{taxonomy_id}/', status_code=HTTPStatus.NO_CONTENT)
async def delete_taxonomy(
    taxonomy_id: UUID,
    conn: Connection = Depends(get_conn),
):
    return await taxonomy_service.delete_taxonomy(conn, taxonomy_id)
