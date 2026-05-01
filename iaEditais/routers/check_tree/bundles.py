from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    BundleCreate,
    BundleDocumentCreate,
    BundleFilter,
    BundleList,
    BundlePublic,
    BundleUpdate,
)
from iaEditais.services import bundle_service

router = APIRouter(
    prefix='/bundle',
    tags=['árvore de verificação, bundles'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=BundlePublic,
)
async def create_bundle(
    bundle: BundleCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await bundle_service.create_bundle(session, current_user.id, bundle)


@router.get('', response_model=BundleList)
async def read_bundles(
    session: Session, filters: Annotated[BundleFilter, Depends()]
):
    bundles = await bundle_service.get_bundles(session, filters)
    return {'bundles': bundles}


@router.get('/{bundle_id}', response_model=BundlePublic)
async def read_bundle(bundle_id: UUID, session: Session):
    return await bundle_service.get_bundle_by_id(session, bundle_id)


@router.put('', response_model=BundlePublic)
async def update_bundle(
    bundle: BundleUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await bundle_service.update_bundle(session, current_user.id, bundle)


@router.delete(
    '/{bundle_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_bundle(
    bundle_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await bundle_service.delete_bundle(session, current_user.id, bundle_id)
    return {'message': 'Bundle deleted'}


@router.post(
    '/{bundle_id}/document',
    status_code=HTTPStatus.CREATED,
    response_model=BundlePublic,
)
async def add_bundle_document(
    bundle_id: UUID,
    document: BundleDocumentCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await bundle_service.add_document(
        session, current_user.id, bundle_id, document
    )


@router.delete(
    '/{bundle_id}/document/{document_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def remove_bundle_document(
    bundle_id: UUID,
    document_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await bundle_service.remove_document(
        session, current_user.id, bundle_id, document_id
    )
    return {'message': 'Bundle document deleted'}
