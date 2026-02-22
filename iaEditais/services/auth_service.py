import secrets
from datetime import datetime, timedelta
from http import HTTPStatus

from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import OAuth2Form
from iaEditais.core.security import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from iaEditais.core.settings import Settings
from iaEditais.models import AccessType, PasswordReset, User
from iaEditais.repositories import user_repo
from iaEditais.schemas import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    Token,
    UserPasswordChange,
    UserPublic,
)
from iaEditais.schemas.common import Message
from iaEditais.services import audit_service, notification_service

SETTINGS = Settings()


async def authenticate_user(
    session: AsyncSession, form_data: OAuth2Form
) -> User:
    user = await user_repo.get_by_email_or_phone(session, form_data.username)
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
    return user


async def login(session: AsyncSession, user: User) -> Token:
    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='LOGIN',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()
    access_token = create_access_token(data={'sub': str(user.id)})
    return {'access_token': access_token, 'token_type': 'bearer'}


async def login_with_cookie(
    session: AsyncSession, user: User, response: Response
) -> Token:
    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='LOGIN_COOKIE',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    access_token = create_access_token(data={'sub': str(user.id)})
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


async def logout(
    session: AsyncSession, user: User, response: Response
) -> Message:
    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='LOGOUT',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()

    response.delete_cookie(
        key=SETTINGS.ACCESS_TOKEN_COOKIE_NAME,
        domain=SETTINGS.COOKIE_DOMAIN,
        path=SETTINGS.COOKIE_PATH,
    )
    return {'message': 'signed out'}


async def refresh_token(session: AsyncSession, user: User) -> Token:
    await audit_service.register_action(
        session=session,
        user_id=user.id,
        action='REFRESH_TOKEN',
        table_name=User.__tablename__,
        record_id=user.id,
        old_data=None,
    )
    await session.commit()
    new_access_token = create_access_token(data={'sub': str(user.id)})
    return {'access_token': new_access_token, 'token_type': 'bearer'}


async def forgot_password(
    session: AsyncSession, payload: ForgotPasswordRequest, broker
) -> dict:
    user = await user_repo.get_by_email_or_phone(session, payload.email)

    if not user:
        # Retornamos sucesso fake para evitar enumeration attack
        return {'message': 'If user exists, a code was sent via WhatsApp'}

    await user_repo.delete_password_reset_by_user(session, user.id)

    reset_token = secrets.token_hex(3).upper()
    token_hash = get_password_hash(reset_token)
    expires_at = datetime.now() + timedelta(minutes=15)

    db_reset = PasswordReset(
        user_id=user.id, token_hash=token_hash, expires_at=expires_at
    )
    user_repo.add_password_reset(session, db_reset)
    await session.commit()

    await notification_service.publish_password_reset_notification(
        user=user, reset_token=reset_token, broker=broker
    )
    return {'message': 'If user exists, a code was sent via WhatsApp'}


async def reset_password(
    session: AsyncSession, payload: ResetPasswordRequest
) -> Message:
    user = await user_repo.get_by_email_or_phone(session, payload.email)
    if not user:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Invalid request'
        )

    reset_entry = await user_repo.get_password_reset(session, user.id)
    if not reset_entry:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Invalid or expired token',
        )

    if datetime.now() > reset_entry.expires_at:
        await user_repo.delete_entry(session, reset_entry)
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

    await user_repo.delete_entry(session, reset_entry)
    await session.commit()

    return {'message': 'Password reset successfully'}


async def change_password(
    session: AsyncSession, current_user: User, payload: UserPasswordChange
) -> Message:
    db_user = await user_repo.get_by_id(session, payload.user_id)

    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    is_owner = db_user.id == current_user.id
    is_admin = current_user.access_level == AccessType.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Unauthorized'
        )

    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    if is_owner:
        if not payload.current_password:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail='Current password required',
            )
        if not verify_password(payload.current_password, db_user.password):
            raise HTTPException(
                status_code=HTTPStatus.UNAUTHORIZED,
                detail='Invalid current password',
            )

    new_password = payload.new_password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Password too short'
        )
    if (
        new_password.lower() == new_password
        or new_password.upper() == new_password
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Password needs mixed case',
        )
    if not any(c.isdigit() for c in new_password):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Password needs number'
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
    return {'message': 'Password updated successfully'}
