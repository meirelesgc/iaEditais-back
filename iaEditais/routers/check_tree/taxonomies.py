from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    TaxonomyCreate,
    TaxonomyList,
    TaxonomyPublic,
    TaxonomyUpdate,
)
from iaEditais.schemas.taxonomy import TaxonomyFilter
from iaEditais.services import taxonomy_service

router = APIRouter(
    prefix='/taxonomy',
    tags=['árvore de verificação, taxonomias'],
)


@router.post('', status_code=HTTPStatus.CREATED, response_model=TaxonomyPublic)
async def create_taxonomy(
    taxonomy: TaxonomyCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await taxonomy_service.create_taxonomy(
        session, current_user.id, taxonomy
    )


@router.get('', response_model=TaxonomyList)
async def read_taxonomies(
    session: Session, filters: Annotated[TaxonomyFilter, Depends()]
):
    taxonomies = await taxonomy_service.get_taxonomies(session, filters)
    return {'taxonomies': taxonomies}


@router.get('/{taxonomy_id}', response_model=TaxonomyPublic)
async def read_taxonomy(taxonomy_id: UUID, session: Session):
    return await taxonomy_service.get_taxonomy_by_id(session, taxonomy_id)


@router.put('', response_model=TaxonomyPublic)
async def update_taxonomy(
    taxonomy: TaxonomyUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await taxonomy_service.update_taxonomy(
        session, current_user.id, taxonomy
    )


@router.delete(
    '/{taxonomy_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_taxonomy(
    taxonomy_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await taxonomy_service.delete_taxonomy(
        session, current_user.id, taxonomy_id
    )
    return {'message': 'Taxonomy deleted'}
