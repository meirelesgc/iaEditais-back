from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.schemas import (
    SourceCreate,
    SourceList,
    SourcePublic,
    SourceUpdate,
)
from iaEditais.schemas.source import SourceFilter
from iaEditais.services import source_service

router = APIRouter(
    prefix='/source',
    tags=['árvore de verificação, fontes'],
)


@router.post('', status_code=HTTPStatus.CREATED, response_model=SourcePublic)
async def create_source(
    source: SourceCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await source_service.create_source(session, current_user.id, source)


@router.get('', response_model=SourceList)
async def read_sources(
    session: Session, filters: Annotated[SourceFilter, Depends()]
):
    sources = await source_service.get_sources(session, filters)
    return {'sources': sources}


@router.post(
    '/{source_id}/upload',
    status_code=HTTPStatus.CREATED,
    response_model=SourcePublic,
)
async def upload_source_document(
    source_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
    file: UploadFile = File(...),
):
    return await source_service.upload_document(
        session, current_user.id, source_id, storage, file
    )


@router.get('/{source_id}', response_model=SourcePublic)
async def read_source(source_id: UUID, session: Session):
    return await source_service.get_source_by_id(session, source_id)


@router.put('', response_model=SourcePublic)
async def update_source(
    source: SourceUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await source_service.update_source(session, current_user.id, source)


@router.delete(
    '/{source_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_source(
    source_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await source_service.delete_source(session, current_user.id, source_id)
    return {'message': 'Source deleted'}
