from http import HTTPStatus
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import Storage
from iaEditais.models import Source
from iaEditais.repositories import source_repo
from iaEditais.schemas import (
    SourceCreate,
    SourcePublic,
    SourceUpdate,
)
from iaEditais.schemas.source import SourceFilter
from iaEditais.services import audit_service


async def create_source(
    session: AsyncSession, user_id: UUID, data: SourceCreate
) -> Source:
    existing_source = await source_repo.get_by_name(session, data.name)
    if existing_source:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Source name already exists',
        )

    db_source = Source(
        name=data.name,
        description=data.description,
    )
    db_source.set_creation_audit(user_id)

    source_repo.add(session, db_source)
    await session.flush()

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_source)
    return db_source


async def get_sources(
    session: AsyncSession, filters: SourceFilter
) -> list[Source]:
    return await source_repo.list_all(session, filters)


async def get_source_by_id(session: AsyncSession, source_id: UUID) -> Source:
    source = await source_repo.get_by_id(session, source_id)
    if not source or source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )
    return source


async def upload_document(
    session: AsyncSession,
    user_id: UUID,
    source_id: UUID,
    storage: Storage,
    file: UploadFile,
) -> Source:
    source = await get_source_by_id(session, source_id)

    old_data = SourcePublic.model_validate(source).model_dump(mode='json')

    if source.file_path:
        await storage.delete(source.file_path)

    unique_filename = f'{uuid4()}_{file.filename}'
    file_path = await storage.save(file, unique_filename)

    source.file_path = file_path
    new_data = SourcePublic.model_validate(source).model_dump(mode='json')
    source.set_update_audit(user_id)

    # Adicionamos novamente para garantir tracking na session, embora o ORM geralmente cuide disso
    source_repo.add(session, source)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Source.__tablename__,
        record_id=source.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(source)
    return source


async def update_source(
    session: AsyncSession, user_id: UUID, data: SourceUpdate
) -> Source:
    db_source = await get_source_by_id(session, data.id)

    old_data = SourcePublic.model_validate(db_source).model_dump(mode='json')

    if data.name != db_source.name:
        conflict = await source_repo.get_by_name(
            session, data.name, exclude_id=data.id
        )
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Source name already exists',
            )

    db_source.name = data.name
    db_source.description = data.description

    new_data = SourcePublic.model_validate(db_source).model_dump(mode='json')
    db_source.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_source)
    return db_source


async def delete_source(
    session: AsyncSession, user_id: UUID, source_id: UUID
) -> None:
    db_source = await get_source_by_id(session, source_id)

    old_data = SourcePublic.model_validate(db_source).model_dump(mode='json')
    db_source.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Source.__tablename__,
        record_id=db_source.id,
        old_data=old_data,
    )

    await session.commit()
