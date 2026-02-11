import secrets
from datetime import datetime, timedelta
from http import HTTPStatus

from fastapi import (
    HTTPException,
    Response,
    status,
)
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import delete, select

from iaEditais.core.dependencies import CurrentUser, OAuth2Form, Session
from iaEditais.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from iaEditais.core.settings import Settings
from iaEditais.models import AccessType, PasswordReset, User
from iaEditais.schemas import (
    Token,
    UserPasswordChange,
    UserPublic,
)
from iaEditais.schemas.common import Message
from iaEditais.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from iaEditais.services import (
    audit_service,
    notification_service,
)

SETTINGS = Settings()
BROKER_URL = SETTINGS.BROKER_URL

router = APIRouter(
    prefix='/auth',
    tags=['operações de sistema, autenticação'],
)


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

    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='LOGIN',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    access_token = create_access_token(data={'sub': user.id})
    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/refresh_token', response_model=Token)
async def refresh_access_token(user: CurrentUser, session: Session):
    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='REFRESH_TOKEN',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    new_access_token = create_access_token(data={'sub': user.id})
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

    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='LOGIN_COOKIE',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    access_token = create_access_token(data={'sub': user.id})

    max_age = SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    response.set_cookie(
        key=SETTINGS.ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,
        max_age=max_age,
        expires=max_age,
        domain=SETTINGS.COOKIE_DOMAIN,
        path=SETTINGS.COOKIE_PATH,
        secure=SETTINGS.COOKIE_SECURE,
        samesite=SETTINGS.COOKIE_SAMESITE,
    )

    return {'access_token': access_token, 'token_type': 'bearer'}


@router.post('/sign-out')
async def sign_out(
    response: Response, session: Session, current_user: CurrentUser
):
    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='LOGOUT',
        table_name=User.__tablename__,
        record_id=current_user.id,
        old_data=None,
    )
    await session.commit()

    response.delete_cookie(
        key=SETTINGS.ACCESS_TOKEN_COOKIE_NAME,
        domain=SETTINGS.COOKIE_DOMAIN,
        path=SETTINGS.COOKIE_PATH,
    )
    return {'detail': 'signed out'}


@router.post('/forgot-password', status_code=HTTPStatus.OK)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: Session,
):
    user = await session.scalar(
        select(User).where(
            User.email == payload.email, User.deleted_at.is_(None)
        )
    )

    if not user:
        return {'message': 'If user exists, a code was sent via WhatsApp'}

    await session.execute(
        delete(PasswordReset).where(PasswordReset.user_id == user.id)
    )

    reset_token = secrets.token_hex(3).upper()
    token_hash = get_password_hash(reset_token)

    expires_at = datetime.now() + timedelta(minutes=15)

    db_reset = PasswordReset(
        user_id=user.id, token_hash=token_hash, expires_at=expires_at
    )

    session.add(db_reset)
    await session.commit()

    await notification_service.publish_password_reset_notification(
        user=user, reset_token=reset_token, broker=router.broker
    )

    return {'message': 'If user exists, a code was sent via WhatsApp'}


@router.post('/reset-password', status_code=HTTPStatus.OK)
async def reset_password(
    payload: ResetPasswordRequest,
    session: Session,
):
    user = await session.scalar(
        select(User).where(
            User.email == payload.email, User.deleted_at.is_(None)
        )
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Invalid request'
        )

    reset_entry = await session.scalar(
        select(PasswordReset).where(PasswordReset.user_id == user.id)
    )

    if not reset_entry:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Invalid or expired token',
        )

    if datetime.now() > reset_entry.expires_at:
        await session.delete(reset_entry)
        await session.commit()
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Token expired'
        )

    if not verify_password(payload.token, reset_entry.token_hash):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Invalid token'
        )

    new_password = payload.new_password
    if len(new_password) < 8 or not any(c.isdigit() for c in new_password):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password requirements not met',
        )

    user.password = get_password_hash(new_password)

    user.set_update_audit(user.id)

    await session.delete(reset_entry)

    await session.commit()

    return {'message': 'Password reset successfully'}


@router.put('/password', response_model=Message)
async def change_password(
    payload: UserPasswordChange,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, payload.user_id)

    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    is_owner = db_user.id == current_user.id
    is_admin = current_user.access_level == AccessType.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='You are not authorized to change this password',
        )

    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    if is_owner:
        if not payload.current_password:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Current password is required',
            )

        if not verify_password(payload.current_password, db_user.password):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Invalid current password',
            )

    new_password = payload.new_password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password must be at least 8 characters long',
        )
    if (
        new_password.lower() == new_password
        or new_password.upper() == new_password
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password must contain both uppercase and lowercase letters',
        )
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password must contain at least one number',
        )

    db_user.password = get_password_hash(new_password)

    new_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    db_user.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()

    return Message(message='Password updated successfully')
