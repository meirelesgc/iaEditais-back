import re
import secrets
from datetime import datetime, timedelta
from http import HTTPStatus
from secrets import token_hex
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import Storage
from iaEditais.core.security import get_password_hash, verify_password
from iaEditais.models import AccessType, PasswordReset, User, UserImage
from iaEditais.repositories import user_repo
from iaEditais.schemas import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserCreate,
    UserFilter,
    UserImagePublic,
    UserPasswordChange,
    UserPublic,
    UserUpdate,
)
from iaEditais.schemas.common import Message
from iaEditais.services import audit_service, notification_service


# Helper function
def normalize_phone(phone):
    if not phone:
        return None
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('55'):
        return digits
    return f'55{digits}'


async def create_user(
    session: AsyncSession, data: UserCreate, broker=None
) -> User:
    norm_phone = normalize_phone(data.phone_number)
    existing_user = await user_repo.get_by_email_or_phone(
        session, data.email, norm_phone
    )

    if existing_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )

    password_was_generated = False
    temp_password = data.password

    if not data.password:
        temp_password = token_hex(12)
        password_was_generated = True

    hashed_password = get_password_hash(temp_password)

    db_user = User(
        username=data.username,
        email=data.email,
        phone_number=norm_phone,
        password=hashed_password,
        access_level=data.access_level,
        unit_id=data.unit_id,
    )

    user_repo.add_user(session, db_user)
    await session.flush()

    db_user.set_creation_audit(db_user.id)

    await audit_service.register_action(
        session=session,
        user_id=db_user.id,
        action='CREATE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_user)

    if password_was_generated and broker:
        await notification_service.publish_user_welcome_notification(
            db_user, temp_password, broker
        )

    return db_user


async def update_user_icon(
    session: AsyncSession,
    user_id: UUID,
    current_user_id: UUID,
    file: UploadFile,
    storage: Storage,
) -> Message:
    user_db = await user_repo.get_by_id(session, user_id)

    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    if user_db.id != current_user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Access denied'
        )

    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Invalid file format'
        )

    old_data = UserPublic.model_validate(user_db).model_dump(mode='json')

    if user_db.icon_id:
        old_icon = await user_repo.get_user_image(session, user_db.icon_id)
        if old_icon:
            await storage.delete(old_icon.file_path)
            await user_repo.delete_entry(session, old_icon)

    unique_filename = f'{uuid4()}_{file.filename}'
    file_path = await storage.save(file, unique_filename)

    user_image = UserImage(
        user_id=current_user_id, type='ICON', file_path=file_path
    )
    user_repo.add_image(session, user_image)
    await session.flush()

    user_db.icon_id = user_image.id

    new_data = UserPublic.model_validate(user_db).model_dump(mode='json')
    new_data['icon'] = UserImagePublic.model_validate(user_image).model_dump(
        mode='json'
    )

    user_db.set_update_audit(current_user_id)

    await audit_service.register_action(
        session=session,
        user_id=current_user_id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=user_db.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    return Message(message='Icon updated successfully')


async def get_users(session: AsyncSession, filters: UserFilter) -> list[User]:
    return await user_repo.list_all(session, filters)


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User:
    user = await user_repo.get_by_id(session, user_id)
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )
    return user


async def update_user(
    session: AsyncSession, current_user: User, data: UserUpdate
) -> User:
    db_user = await user_repo.get_by_id(session, data.id)

    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    is_owner = db_user.id == current_user.id
    is_admin = current_user.access_level == AccessType.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='You are not authorized to update this user',
        )

    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    norm_phone = normalize_phone(data.phone_number)
    conflict_user = await user_repo.get_conflict_user(
        session, data.id, data.email, norm_phone
    )

    if conflict_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )

    db_user.username = data.username
    db_user.email = data.email
    db_user.phone_number = norm_phone

    if is_admin:
        db_user.access_level = data.access_level
        db_user.unit_id = data.unit_id

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
    await session.refresh(db_user)
    return db_user


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
    # Validações de senha
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
    return Message(message='Password updated successfully')


async def delete_user(
    session: AsyncSession, current_user_id: UUID, user_id: UUID
) -> None:
    db_user = await user_repo.get_by_id(session, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')
    db_user.set_deletion_audit(current_user_id)

    await audit_service.register_action(
        session=session,
        user_id=current_user_id,
        action='DELETE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=old_data,
    )
    await session.commit()


async def delete_user_icon(
    session: AsyncSession,
    current_user_id: UUID,
    user_id: UUID,
    storage: Storage,
) -> Message:
    user_db = await user_repo.get_by_id(session, user_id)
    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    if user_db.id != current_user_id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Access denied'
        )

    if not user_db.icon_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Icon not found'
        )

    old_data = UserPublic.model_validate(user_db).model_dump(mode='json')
    user_image = await user_repo.get_user_image(session, user_db.icon_id)

    if user_image:
        await storage.delete(user_image.file_path)
        await user_repo.delete_entry(session, user_image)

    user_db.icon_id = None
    new_data = UserPublic.model_validate(user_db).model_dump(mode='json')
    user_db.set_update_audit(current_user_id)

    await audit_service.register_action(
        session=session,
        user_id=current_user_id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=user_db.id,
        old_data=old_data,
        new_data=new_data,
    )
    await session.commit()
    return Message(message='Icon successfully deleted!')


async def test_whatsapp(
    session: AsyncSession, current_user: User, user_id: UUID, broker
) -> Message:
    db_user = await user_repo.get_by_id(session, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    if (
        db_user.id != current_user.id
        and current_user.access_level != AccessType.ADMIN
    ):
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN, detail='Access denied'
        )

    if not db_user.phone_number:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='User has no phone number',
        )

    result = await notification_service.publish_test_whatsapp_notification(
        db_user, broker
    )

    if result['status'] == 'error':
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=result['detail']
        )

    return Message(
        message='Test message sent to WhatsApp queue. Check your device.'
    )


async def forgot_password(
    session: AsyncSession, payload: ForgotPasswordRequest, broker
) -> dict:
    user = await user_repo.get_by_email_or_phone(session, payload.email)

    if not user:
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
) -> dict:
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
