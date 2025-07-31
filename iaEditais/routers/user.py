from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import user_model
from iaEditais.security import get_current_user
from iaEditais.services import user_service

router = APIRouter()


@router.post(
    '/user/',
    status_code=HTTPStatus.CREATED,
    response_model=user_model.UserResponse,
)
async def post_user(
    user: user_model.CreateUser,
    conn: Connection = Depends(get_conn),
):
    return await user_service.post_user(conn, user)


@router.get(
    '/user/',
    status_code=HTTPStatus.OK,
    response_model=list[user_model.UserResponse],
)
async def get_user(conn: Connection = Depends(get_conn)):
    return await user_service.get_user(conn)


@router.get(
    '/user/{id}/',
    status_code=HTTPStatus.OK,
    response_model=user_model.UserResponse,
)
async def get_single_user(id: UUID, conn: Connection = Depends(get_conn)):
    return await user_service.get_user(conn, id)


@router.put(
    '/user/',
    status_code=HTTPStatus.OK,
    response_model=user_model.User,
)
async def put_user(
    user: user_model.UserUpdate,
    current_user: user_model.User = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
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
async def delete_user(
    id: UUID,
    current_user: user_model.User = Depends(get_current_user),
    conn: Connection = Depends(get_conn),
):
    return await user_service.delete_user(conn, id)


@router.post('/token/', response_model=user_model.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    conn: Connection = Depends(get_conn),
):
    return await user_service.login_for_access_token(conn, form_data)
