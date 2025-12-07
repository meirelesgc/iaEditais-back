import os
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Source
from iaEditais.schemas import (
    FilterPage,
    SourceCreate,
    SourceList,
    SourcePublic,
    SourceUpdate,
)
from iaEditais.services import storage_service

router = APIRouter(prefix='/source', tags=['árvore de verificação, fontes'])

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


@router.post('/', status_code=HTTPStatus.CREATED, response_model=SourcePublic)
async def create_source(
    source: SourceCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_source = await session.scalar(
        select(Source).where(
            Source.deleted_at.is_(None), Source.name == source.name
        )
    )

    if db_source:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Source name already exists',
        )

    db_source = Source(
        name=source.name,
        description=source.description,
        created_by=current_user.id,
    )

    session.add(db_source)
    await session.commit()
    await session.refresh(db_source)

    return db_source


@router.get('/', response_model=SourceList)
async def read_sources(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Source)
        .where(Source.deleted_at.is_(None))
        .order_by(Source.created_at.desc())
        .offset(filters.offset)
        .limit(filters.limit)
    )

    sources = query.all()
    return {'sources': sources}


@router.post(
    '/{source_id}/upload',
    status_code=HTTPStatus.CREATED,
    response_model=SourcePublic,
)
async def upload_source_document(
    source_id: UUID,
    session: Session,
    file: UploadFile = File(...),
):
    source = await session.get(Source, source_id)
    if not source or source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Source not found'
        )

    if source.file_path and os.path.exists(source.file_path):
        unique_filename = source.file_path.split('/')[-1]
        file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
        os.remove(file_path)

    file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)

    source.file_path = file_path
    source.updated_at = datetime.now()
    session.add(source)
    await session.commit()

    await router.broker.publish(source.id, 'sources_create_vectors')
    return source


@router.get('/{source_id}', response_model=SourcePublic)
async def read_source(source_id: UUID, session: Session):
    source = await session.get(Source, source_id)

    if not source or source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    return source


@router.put('/', response_model=SourcePublic)
async def update_source(
    source: SourceUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_source = await session.get(Source, source.id)

    if not db_source or db_source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    db_source_same_name = await session.scalar(
        select(Source).where(
            Source.deleted_at.is_(None), Source.name == source.name
        )
    )

    if db_source_same_name:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Source name already exists',
        )

    db_source.name = source.name
    db_source.description = source.description
    db_source.updated_by = current_user.id

    await session.commit()
    await session.refresh(db_source)

    return db_source


@router.delete(
    '/{source_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_source(
    source_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_source = await session.get(Source, source_id)

    if not db_source or db_source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    db_source.deleted_at = datetime.now(timezone.utc)
    db_source.deleted_by = current_user.id
    await session.commit()

    return {'message': 'Source deleted'}
