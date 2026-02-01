from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.core.settings import Settings
from iaEditais.models import Source
from iaEditais.schemas import (
    FilterPage,
    SourceCreate,
    SourceList,
    SourcePublic,
    SourceUpdate,
)
from iaEditais.services import audit_service

SETTINGS = Settings()
BROKER_URL = SETTINGS.BROKER_URL

router = APIRouter(
    prefix='/source',
    tags=['árvore de verificação, fontes'],
)

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
    )

    db_source.set_creation_audit(current_user.id)

    session.add(db_source)

    await session.flush()

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=None,
    )

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


from uuid import uuid4


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
    source = await session.get(Source, source_id)
    if not source or source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    old_data = SourcePublic.model_validate(source).model_dump(mode='json')

    if source.file_path:
        await storage.delete(source.file_path)

    unique_filename = f'{uuid4()}_{file.filename}'
    file_path = await storage.save(file, unique_filename)

    source.file_path = file_path

    new_data = SourcePublic.model_validate(source).model_dump(mode='json')

    source.set_update_audit(current_user.id)

    session.add(source)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Source.__tablename__,
        record_id=source.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(source)

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

    old_data = SourcePublic.model_validate(db_source).model_dump(mode='json')

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

    new_data = SourcePublic.model_validate(db_source).model_dump(mode='json')

    db_source.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=old_data,
        new_data=new_data,
    )

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

    old_data = SourcePublic.model_validate(db_source).model_dump(mode='json')

    db_source.set_deletion_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=old_data,
    )

    await session.commit()

    return {'message': 'Source deleted'}
