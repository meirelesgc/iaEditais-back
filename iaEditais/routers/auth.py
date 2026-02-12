from http import HTTPStatus

from fastapi import Response
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, OAuth2Form, Session
from iaEditais.schemas import (
    Token,
    UserPasswordChange,
)
from iaEditais.schemas.common import Message
from iaEditais.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from iaEditais.services import auth_service

router = APIRouter(
    prefix='/auth',
    tags=['operações de sistema, autenticação'],
)


@router.post('/token', response_model=Token)
async def login_for_access_token(form_data: OAuth2Form, session: Session):
    user = await auth_service.authenticate_user(session, form_data)
    return await auth_service.login(session, user)


@router.post('/refresh_token', response_model=Token)
async def refresh_access_token(user: CurrentUser, session: Session):
    return await auth_service.refresh_token(session, user)


@router.post('/sign-in', response_model=Token)
async def sign_in_for_cookie(
    form_data: OAuth2Form, response: Response, session: Session
):
    user = await auth_service.authenticate_user(session, form_data)
    return await auth_service.login_with_cookie(session, user, response)


@router.post('/sign-out')
async def sign_out(
    response: Response, session: Session, current_user: CurrentUser
):
    return await auth_service.logout(session, current_user, response)


@router.post('/forgot-password', status_code=HTTPStatus.OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: Session,
):
    return await auth_service.forgot_password(session, payload, router.broker)


@router.post('/reset-password', status_code=HTTPStatus.OK)
async def reset_password(
    payload: ResetPasswordRequest,
    session: Session,
):
    return await auth_service.reset_password(session, payload)


@router.put('/password', response_model=Message)
async def change_password(
    payload: UserPasswordChange,
    session: Session,
    current_user: CurrentUser,
):
    return await auth_service.change_password(session, current_user, payload)
