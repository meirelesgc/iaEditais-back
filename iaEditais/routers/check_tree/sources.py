import os
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
from iaEditais.services import audit, storage_service

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

    # 1. Criação do objeto (AuditMixin trata created_by)
    db_source = Source(
        name=source.name,
        description=source.description,
    )
    # 2. Preenche created_at e created_by via Mixin
    db_source.set_creation_audit(current_user.id)

    session.add(db_source)
    # Flush para garantir ID antes do log
    await session.flush()

    # 3. Registro de Auditoria (CREATE)
    await audit.register_action(
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


@router.post(
    '/{source_id}/upload',
    status_code=HTTPStatus.CREATED,
    response_model=SourcePublic,
)
async def upload_source_document(
    source_id: UUID,
    session: Session,
    current_user: CurrentUser,  # Adicionado para auditoria
    file: UploadFile = File(...),
):
    source = await session.get(Source, source_id)
    if not source or source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Source not found'
        )
    # 4. Snapshot antes do upload (que altera o file_path)
    old_data = SourcePublic.model_validate(source).model_dump(mode='json')

    if source.file_path and os.path.exists(source.file_path):
        unique_filename = source.file_path.split('/')[-1]
        file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
        os.remove(file_path)

    file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)

    source.file_path = file_path

    # 5. Preenche updated_at e updated_by via Mixin
    source.set_update_audit(current_user.id)

    session.add(source)

    # 6. Registro de Auditoria (UPDATE - Upload de arquivo)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Source.__tablename__,
        record_id=source.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(source)
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

    # 7. Snapshot antes da atualização
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

    # 8. Preenche updated_at e updated_by via Mixin
    db_source.set_update_audit(current_user.id)

    # 9. Registro de Auditoria (UPDATE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=old_data,
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

    # 10. Snapshot antes de deletar
    old_data = SourcePublic.model_validate(db_source).model_dump(mode='json')

    # 11. Soft delete via Mixin
    db_source.set_deletion_audit(current_user.id)

    # 12. Registro de Auditoria (DELETE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=old_data,
    )

    await session.commit()

    return {'message': 'Source deleted'}
