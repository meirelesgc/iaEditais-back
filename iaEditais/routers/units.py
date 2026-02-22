from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    UnitCreate,
    UnitFilter,
    UnitList,
    UnitPublic,
    UnitUpdate,
)
from iaEditais.services import unit_service

router = APIRouter(prefix='/unit', tags=['operações de sistema, unidades'])


@router.post('', status_code=HTTPStatus.CREATED, response_model=UnitPublic)
async def create_unit(
    unit: UnitCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await unit_service.create_unit(session, current_user.id, unit)


@router.get('', response_model=UnitList)
async def read_units(
    session: Session, filters: Annotated[UnitFilter, Depends()]
):
    units = await unit_service.get_units(session, filters)
    return {'units': units}


@router.get('/{unit_id}', response_model=UnitPublic)
async def read_unit(unit_id: UUID, session: Session):
    return await unit_service.get_unit_by_id(session, unit_id)


@router.put('', response_model=UnitPublic)
async def update_unit(
    unit: UnitUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await unit_service.update_unit(session, current_user.id, unit)


@router.delete('/{unit_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_unit(
    unit_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await unit_service.delete_unit(session, current_user.id, unit_id)
    return {'message': 'Unit deleted'}
