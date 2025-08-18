from datetime import datetime
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr

from iaEditais.core.connection import Connection
from iaEditais.models import user_model
from iaEditais.repositories import user_repository
from iaEditais.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)


async def post_user(conn: Connection, user: user_model.CreateUser):
    user = user_model.User(**user.model_dump())
    user.password = get_password_hash(user.password)
    await user_repository.post_user(conn, user)
    return user


async def get_user(
    conn: Connection,
    id: UUID = None,
    email: EmailStr = None,
    unit_id: UUID = None,
):
    users = await user_repository.get_user(conn, id, email, unit_id)
    return users


async def put_user(conn: Connection, user: user_model.UserUpdate):
    if not user.password:
        user.password = await get_user(user.id).password

    user = user_model.User(**user.model_dump())
    user.updated_at = datetime.now()
    user.password = get_password_hash(user.password)
    await user_repository.put_user(conn, user)
    return user


async def delete_user(conn: Connection, id: UUID = None):
    await user_repository.delete_user(conn, id)


async def login_for_access_token(
    response: Response,
    conn: Connection,
    form_data: OAuth2PasswordRequestForm,
):
    user = await get_user(conn, None, form_data.username)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Incorrect email or password',
        )
    if not verify_password(form_data.password, user['password']):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Incorrect email or password',
        )
    access_token = create_access_token(data={'sub': user['email']})
    response.set_cookie(
        key='access_token',
        value=access_token,
        httponly=True,
        samesite='strict',
        secure=False,
        max_age=1800,
    )
    return {'access_token': access_token, 'token_type': 'bearer'}
