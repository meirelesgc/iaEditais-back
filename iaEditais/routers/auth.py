from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import User
from iaEditais.schemas import Token
from iaEditais.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    create_access_token,
    get_current_user,
    verify_password,
)
from iaEditais.settings import Settings

settings = Settings()

router = APIRouter(prefix='/auth', tags=['autenticação'])

OAuth2Form = Annotated[OAuth2PasswordRequestForm, Depends()]
Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post('/token', response_model=Token)
async def login_for_access_token(form_data: OAuth2Form, session: Session):
    user = await session.scalar(
        select(User).where(User.email == form_data.username)
    )
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Incorrect email or password',
        )
    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Incorrect email or password',
        )
    access_token = create_access_token(data={'sub': user.email})
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh_token', response_model=Token)
async def refresh_access_token(user: CurrentUser):
    new_access_token = create_access_token(data={'sub': user.email})
    return {'access_token': new_access_token, 'token_type': 'bearer'}


@router.post('/sign-in', response_model=Token)
async def sign_in_for_cookie(
    form_data: OAuth2Form, response: Response, session: Session
):
    user = await session.scalar(
        select(User).where(User.email == form_data.username)
    )
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Incorrect email or password',
        )
    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=HTTPStatus.UNAUTHORIZED,
            detail='Incorrect email or password',
        )
    access_token = create_access_token(data={'sub': user.email})
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        path='/',
        secure=True,
        samesite='lax',
    )
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/sign-out')
async def sign_out(response: Response):
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME, path='/')
    return {'detail': 'signed out'}
