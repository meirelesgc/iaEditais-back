from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Unit
from iaEditais.schemas import (
    FilterPage,
    Message,
    UnitCreate,
    UnitList,
    UnitPublic,
    UnitUpdate,
)

router = APIRouter(prefix='/unit', tags=['units'])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UnitPublic)
async def create_unit(unit: UnitCreate, session: Session):
    db_unit = await session.scalar(
        select(Unit).where(Unit.deleted_at.is_(None), Unit.name == unit.name)
    )

    if db_unit:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unit name already exists',
        )

    db_unit = Unit(name=unit.name, location=unit.location)

    session.add(db_unit)
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
        .offset(filter_units.offset)
        .limit(filter_units.limit)
    )

    units = query.all()
    return {'units': units}


@router.get('/{unit_id}', response_model=UnitPublic)
async def read_unit(unit_id: UUID, session: Session):
    unit = await session.get(Unit, unit_id)

    if not unit or unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )

    return unit


@router.put('/', response_model=UnitPublic)
async def update_unit(unit: UnitUpdate, session: Session):
    db_unit = await session.get(Unit, unit.id)

    if not db_unit or db_unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )

    db_unit.name = unit.name
    db_unit.location = unit.location

    try:
        await session.commit()
        await session.refresh(db_unit)
        return db_unit
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Unit name already exists',
        )


@router.delete('/{unit_id}', response_model=Message)
async def delete_unit(unit_id: UUID, session: Session):
    db_unit = await session.get(Unit, unit_id)

    if not db_unit or db_unit.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Unit not found',
        )

    db_unit.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    return {'message': 'Unit deleted'}
