from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Unit
from iaEditais.repositories import unit_repo
from iaEditais.schemas import UnitCreate, UnitFilter, UnitPublic, UnitUpdate
from iaEditais.services import audit_service


async def create_unit(
    session: AsyncSession, user_id: UUID, data: UnitCreate
) -> Unit:
    existing_unit = await unit_repo.get_by_name(session, data.name)
    if existing_unit:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unit name already exists',
        )

    db_unit = Unit(name=data.name, location=data.location)
    db_unit.set_creation_audit(user_id)

    unit_repo.add(session, db_unit)
    await session.flush()

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Unit.__tablename__,
        record_id=db_unit.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_unit)
    return db_unit


async def get_units(session: AsyncSession, filters: UnitFilter) -> list[Unit]:
    return await unit_repo.list_all(session, filters)


async def get_unit_by_id(session: AsyncSession, unit_id: UUID) -> Unit:
    unit = await unit_repo.get_by_id(session, unit_id)
    if not unit or unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )
    return unit


async def update_unit(
    session: AsyncSession, user_id: UUID, data: UnitUpdate
) -> Unit:
    db_unit = await get_unit_by_id(session, data.id)

    conflict_unit = await unit_repo.get_by_name(
        session, data.name, exclude_id=data.id
    )
    if conflict_unit:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unit name already exists',
        )

    old_data = UnitPublic.model_validate(db_unit).model_dump(mode='json')

    db_unit.name = data.name
    db_unit.location = data.location

    new_data = UnitPublic.model_validate(db_unit).model_dump(mode='json')

    db_unit.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Unit.__tablename__,
        record_id=db_unit.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_unit)
    return db_unit


async def delete_unit(session: AsyncSession, user_id: UUID, unit_id: UUID):
    db_unit = await get_unit_by_id(session, unit_id)

    old_data = UnitPublic.model_validate(db_unit).model_dump(mode='json')
    db_unit.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Unit.__tablename__,
        record_id=db_unit.id,
        old_data=old_data,
    )

    await session.commit()
