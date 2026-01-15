from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, OAuth2Form, Session
from iaEditais.core.security import (
    create_access_token,
    verify_password,
)
from iaEditais.core.settings import Settings
from iaEditais.models import User
from iaEditais.schemas import Token
from iaEditais.services import audit

SETTINGS = Settings()

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

    # Registro de Auditoria (LOGIN)
    await audit.register_action(
        session=session,
        user_id=user.id,
        action='LOGIN',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    access_token = create_access_token(data={'sub': user.email})
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh_token', response_model=Token)
async def refresh_access_token(user: CurrentUser, session: Session):
    # Registro de Auditoria (REFRESH_TOKEN)
    await audit.register_action(
        session=session,
        user_id=user.id,
        action='REFRESH_TOKEN',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

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

    # Registro de Auditoria (LOGIN_COOKIE)
    await audit.register_action(
        session=session,
        user_id=user.id,
        action='LOGIN_COOKIE',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    access_token = create_access_token(data={'sub': user.email})

    max_age = SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    response.set_cookie(
        key=SETTINGS.ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        path=SETTINGS.COOKIE_PATH,
        secure=SETTINGS.COOKIE_SECURE,
        samesite=SETTINGS.COOKIE_SAMESITE,
    )

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/sign-out')
async def sign_out(
    response: Response, session: Session, current_user: CurrentUser
):
    # Registro de Auditoria (LOGOUT)
    # Exige CurrentUser para saber quem está saindo
    await audit.register_action(
        session=session,
        user_id=current_user.id,
        action='LOGOUT',
        table_name=User.__tablename__,
        record_id=current_user.id,
        old_data=None,
    )
    await session.commit()

    response.delete_cookie(SETTINGS.ACCESS_TOKEN_COOKIE_NAME, path='/')
    return {'detail': 'signed out'}
