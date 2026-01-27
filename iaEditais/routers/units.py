from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Unit
from iaEditais.schemas import (
    FilterPage,
    UnitCreate,
    UnitList,
    UnitPublic,
    UnitUpdate,
)
from iaEditais.services import (
    audit,  # Certifique-se de ter criado este serviço
)

router = APIRouter(prefix='/unit', tags=['operações de sistema, unidades'])


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UnitPublic)
async def create_unit(
    unit: UnitCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_unit = await session.scalar(
        select(Unit).where(Unit.deleted_at.is_(None), Unit.name == unit.name)
    )

    if db_unit:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unit name already exists',
        )

    # Criação do objeto (AuditMixin campos não estão no init)
    db_unit = Unit(
        name=unit.name,
        location=unit.location,
    )
    # 1. Preenche created_at e created_by via Mixin
    db_unit.set_creation_audit(current_user.id)

    session.add(db_unit)
    # Flush para garantir que o ID seja gerado antes do registro de auditoria
    await session.flush()

    # 2. Registro de Auditoria (CREATE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Unit.__tablename__,
        record_id=db_unit.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_unit)

    return db_unit


@router.get('/', response_model=UnitList)
async def read_units(
    session: Session, filter_units: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Unit)
        .where(Unit.deleted_at.is_(None))
        .order_by(Unit.created_at.desc())
        .offset(filter_units.offset)
        .limit(filter_units.limit)
    )

    units = query.all()
    return {'units': units}


@router.get('/{unit_id}', response_model=UnitPublic)
async def read_unit(unit_id: UUID, session: Session):
    result = await session.execute(select(Unit).where(Unit.id == unit_id))

    unit = result.scalar_one_or_none()

    if not unit or unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )

    return unit


@router.put('/', response_model=UnitPublic)
async def update_unit(
    unit: UnitUpdate,
    session: Session,
    current_user: CurrentUser,
):
    result = await session.execute(select(Unit).where(Unit.id == unit.id))

    db_unit = result.scalar_one_or_none()

    if not db_unit or db_unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )

    # 3. Snapshot dos dados antes da alteração para o AuditLog
    old_data = UnitPublic.model_validate(db_unit).model_dump(mode='json')

    conflict_unit = await session.scalar(
        select(Unit).where(
            Unit.deleted_at.is_(None),
            Unit.name == unit.name,
            Unit.id != unit.id,
        )
    )
    if conflict_unit:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unit name already exists',
        )

    db_unit.name = unit.name
    db_unit.location = unit.location

    # 4. Preenche updated_at e updated_by via Mixin
    db_unit.set_update_audit(current_user.id)

    # 5. Registro de Auditoria (UPDATE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Unit.__tablename__,
        record_id=db_unit.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(db_unit)
    return db_unit


@router.delete(
    '/{unit_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_unit(
    unit_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    result = await session.execute(select(Unit).where(Unit.id == unit_id))

    db_unit = result.scalar_one_or_none()

    if not db_unit or db_unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )

    # 6. Snapshot antes de deletar
    old_data = UnitPublic.model_validate(db_unit).model_dump(mode='json')

    # 7. Soft delete via Mixin (updated_at=func.now(), deleted_by=user_id)
    db_unit.set_deletion_audit(current_user.id)

    # 8. Registro de Auditoria (DELETE)
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Unit.__tablename__,
        record_id=db_unit.id,
        old_data=old_data,
    )

    await session.commit()

    return {'message': 'Unit deleted'}
