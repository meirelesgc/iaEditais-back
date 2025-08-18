from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import user_model
from iaEditais.security import get_current_user
from iaEditais.services import user_service

router = APIRouter()

Conn = Annotated[Connection, Depends(get_conn)]
CurrentUser = Annotated[user_model.User, Depends(get_current_user)]


@router.post(
    '/user/',
    status_code=HTTPStatus.CREATED,
    response_model=user_model.UserResponse,
)
async def post_user(conn: Conn, user: CurrentUser):
    return await user_service.post_user(conn, user)


@router.get(
    '/user/',
    status_code=HTTPStatus.OK,
    response_model=list[user_model.UserResponse],
)
async def get_user(conn: Conn, unit_id: UUID = None):
    return await user_service.get_user(conn, None, None, unit_id)


@router.get('/user/my-self/', response_model=user_model.UserResponse)
async def get_me(current_user: CurrentUser):
    return current_user


@router.get(
    '/user/{id}/',
    status_code=HTTPStatus.OK,
    response_model=user_model.UserResponse,
)
async def get_single_user(id: UUID, conn: Conn):
    return await user_service.get_user(conn, id)


@router.put('/user/', status_code=HTTPStatus.OK, response_model=user_model.User)
async def put_user(
    user: user_model.UserUpdate, current_user: CurrentUser, conn: Conn
):
    forbidden_exception = HTTPException(
        status_code=HTTPStatus.FORBIDDEN, detail='Not enough permissions'
    )
    if current_user.id != user.id and current_user.access_level != 'ADMIN':
        raise forbidden_exception
    if current_user.access_level == 'DEFAULT' and user.access_level == 'ADMIN':
        raise forbidden_exception

    return await user_service.put_user(conn, user)


@router.delete(
    '/user/{id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_user(id: UUID, current_user: CurrentUser, conn: Conn):
    return await user_service.delete_user(conn, id)
