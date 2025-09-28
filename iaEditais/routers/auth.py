from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, OAuth2Form, Session
from iaEditais.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    create_access_token,
    verify_password,
)
from iaEditais.core.settings import Settings
from iaEditais.models import User
from iaEditais.schemas import Token

settings = Settings()

router = APIRouter(prefix='/auth', tags=['operações de sistema, autenticação'])


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
