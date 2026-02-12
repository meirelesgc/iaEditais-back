from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Typification, TypificationSource
from iaEditais.repositories import typification_repo
from iaEditais.schemas import (
    TypificationCreate,
    TypificationFilter,
    TypificationList,
    TypificationPublic,
    TypificationUpdate,
)
from iaEditais.schemas.source import SourceList
from iaEditais.services import audit_service
from iaEditais.services.report_service import typification_report


async def create_typification(
    session: AsyncSession, user_id: UUID, data: TypificationCreate
) -> Typification:
    existing_typification = await typification_repo.get_by_name(
        session, data.name
    )
    if existing_typification:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Typification name already exists',
        )

    db_typification = Typification(name=data.name)
    db_typification.set_creation_audit(user_id)

    typification_repo.add_typification(session, db_typification)
    await session.flush()

    if data.source_ids:
        sources = await typification_repo.get_sources_by_ids(
            session, data.source_ids
        )
        existing_source_ids = {s.id for s in sources}

        if len(existing_source_ids) != len(data.source_ids):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='One or more sources not found',
            )

        for source_id in data.source_ids:
            association_entry = TypificationSource(
                typification_id=db_typification.id,
                source_id=source_id,
                created_by=user_id,
            )
            typification_repo.add_typification_source(
                session, association_entry
            )

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Typification.__tablename__,
        record_id=db_typification.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_typification)
    return db_typification


async def get_typifications(
    session: AsyncSession, filters: TypificationFilter
) -> list[Typification]:
    return await typification_repo.list_all(session, filters)


async def get_typification_by_id(
    session: AsyncSession, typification_id: UUID
) -> Typification:
    typification = await typification_repo.get_by_id(session, typification_id)
    if not typification or typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )
    return typification


async def update_typification(
    session: AsyncSession, user_id: UUID, data: TypificationUpdate
) -> Typification:
    db_typification = await typification_repo.get_by_id(session, data.id)

    if not db_typification or db_typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    old_data = TypificationPublic.model_validate(db_typification).model_dump(
        mode='json'
    )

    conflict = await typification_repo.get_by_name(
        session, data.name, exclude_id=data.id
    )
    if conflict:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Typification name already exists',
        )

    db_typification.name = data.name

    new_data = TypificationPublic.model_validate(db_typification).model_dump(
        mode='json'
    )

    if data.source_ids:
        sources = await typification_repo.get_sources_by_ids(
            session, data.source_ids
        )
        sources_list = list(sources)
        db_typification.sources = sources_list
        new_data['sources'] = SourceList.model_validate({
            'sources': sources_list
        }).model_dump()
    else:
        db_typification.sources = []

    db_typification.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Typification.__tablename__,
        record_id=db_typification.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_typification)
    return db_typification


async def delete_typification(
    session: AsyncSession, user_id: UUID, typification_id: UUID
) -> None:
    db_typification = await typification_repo.get_by_id(
        session, typification_id
    )

    if not db_typification or db_typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    old_data = TypificationPublic.model_validate(db_typification).model_dump(
        mode='json'
    )
    db_typification.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Typification.__tablename__,
        record_id=db_typification.id,
        old_data=old_data,
    )

    await session.commit()


async def export_pdf(
    session: AsyncSession, typification_id: UUID = None
) -> FileResponse:
    typifications = await typification_repo.list_for_report(
        session, typification_id
    )

    if not typifications:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='No typifications found',
        )

    typifications_list = TypificationList(
        typifications=typifications
    ).model_dump()
    report_path = typification_report(typifications_list)
    return FileResponse(report_path, filename=report_path.split('/')[-1])
