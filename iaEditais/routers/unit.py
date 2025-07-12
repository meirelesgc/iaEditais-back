from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import unit_model
from iaEditais.services import unit_service

router = APIRouter()


@router.post(
    '/unit/',
    status_code=HTTPStatus.CREATED,
    response_model=unit_model.UnitResponse,
)
async def unit_post(
    unit: unit_model.CreateUnit,
    conn: Connection = Depends(get_conn),
):
    return await unit_service.unit_post(conn, unit)


@router.get(
    '/unit/',
    status_code=HTTPStatus.OK,
    response_model=list[unit_model.UnitResponse],
)
async def unit_get(conn: Connection = Depends(get_conn)):
    return await unit_service.unit_get(conn, None)


@router.get(
    '/unit/{id}/',
    status_code=HTTPStatus.OK,
    response_model=unit_model.UnitResponse,
)
async def unit_get_detail(id: UUID, conn: Connection = Depends(get_conn)):
    unit = await unit_service.unit_get(conn, id)
    if not unit:
        raise HTTPException(status_code=404, detail='Unit not found')
    return unit


@router.put(
    '/unit/',
    status_code=HTTPStatus.OK,
    response_model=unit_model.UnitResponse,
)
async def unit_put(
    unit: unit_model.UnitUpdate,
    conn: Connection = Depends(get_conn),
):
    return await unit_service.unit_put(conn, unit)


@router.delete('/unit/{id}/', status_code=HTTPStatus.NO_CONTENT)
async def unit_delete(id: UUID, conn: Connection = Depends(get_conn)):
    return await unit_service.unit_delete(conn, id)
