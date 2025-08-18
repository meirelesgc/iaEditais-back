from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import auth_schemas, user_model
from iaEditais.security import create_access_token, get_current_user
from iaEditais.services import user_service

router = APIRouter(prefix='/auth')

Conn = Annotated[Connection, Depends(get_conn)]
CurrentUser = Annotated[user_model.User, Depends(get_current_user)]


@router.post('/login', response_model=user_model.Token)
async def login_for_access_token(
    conn: Conn,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    return await user_service.login_for_access_token(response, conn, form_data)


@router.post('/refresh_login', response_model=user_model.Token)
async def refresh_access_token(
    user: CurrentUser,
    response: Response,
):
    new_access_token = create_access_token(data={'sub': user.email})
    response.set_cookie(
        key='access_token',
        value=new_access_token,
        httponly=True,
        samesite='strict',
        secure=False,
        max_age=1800,
    )
    return {'access_token': new_access_token, 'token_type': 'bearer'}


@router.post('/logout', status_code=204)
async def logout(response: Response):
    response.delete_cookie(
        key='access_token',
        samesite='strict',
        secure=False,
        httponly=True,
        path='/',
    )


@router.post('/password-reset/request')
async def password_reset(auth_schemas: auth_schemas.PasswordResetRequest): ...
