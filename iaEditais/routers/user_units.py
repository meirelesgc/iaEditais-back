from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import user_units
from iaEditais.services import user_unit_service

router = APIRouter()


@router.post('/user_units/', status_code=HTTPStatus.CREATED)
async def user_unit_post(
    user_unit: user_units.CreateUserUnit, conn: Connection = Depends(get_conn)
):
    await user_unit_service.user_unit_post(conn, user_unit)
    return {'message': 'User linked to Unit successfully'}


@router.delete('/user_units/', status_code=HTTPStatus.NO_CONTENT)
async def user_unit_delete(
    user_id: UUID, unit_id: UUID, conn: Connection = Depends(get_conn)
):
    await user_unit_service.user_unit_delete(conn, user_id, unit_id)


@router.get('/user_units/user/{user_id}/', status_code=HTTPStatus.OK)
async def user_unit_get_user(
    user_id: UUID, conn: Connection = Depends(get_conn)
):
    units = await user_unit_service.user_unit_get_user(conn, user_id)
    return units


@router.get('/user_units/unit/{unit_id}/', status_code=HTTPStatus.OK)
async def user_unit_get_unity(
    unit_id: UUID, conn: Connection = Depends(get_conn)
):
    users = await user_unit_service.user_unit_get_unity(conn, unit_id)
    return users
