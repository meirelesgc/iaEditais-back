import secrets
from datetime import datetime, timedelta
from http import HTTPStatus
from secrets import token_hex
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, File, HTTPException, UploadFile, status
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import delete, or_, select

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.core.security import get_password_hash, verify_password
from iaEditais.core.settings import Settings
from iaEditais.models import AccessType, PasswordReset, User, UserImage
from iaEditais.schemas import (
    UserCreate,
    UserFilter,
    UserList,
    UserPasswordChange,
    UserPublic,
    UserUpdate,
)
from iaEditais.schemas.common import Message
from iaEditais.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserImagePublic,
)
from iaEditais.services import audit_service, notification_service

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'
SETTINGS = Settings()
BROKER_URL = SETTINGS.BROKER_URL

router = APIRouter(
    prefix='/user',
    tags=['operações de sistema, usuário'],
)


@router.post('/', status_code=HTTPStatus.CREATED, response_model=UserPublic)
async def create_user(user: UserCreate, session: Session):
    db_user = await session.scalar(
        select(User).where(
            User.deleted_at.is_(None),
            or_(
                User.email == user.email,
                User.phone_number == user.phone_number,
            ),
        )
    )
    if db_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )
    password_was_generated = False
    temp_password = user.password

    if not user.password:
        temp_password = token_hex(12)
        password_was_generated = True

    hashed_password = get_password_hash(temp_password)

    db_user = User(
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        password=hashed_password,
        access_level=user.access_level,
        unit_id=user.unit_id,
    )

    session.add(db_user)

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

    if password_was_generated:
        await notification_service.publish_user_welcome_notification(
            db_user, temp_password, router.broker
        )

    return db_user


@router.post('/{user_id}/icon', response_model=Message)
async def add_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
    file: UploadFile = File(...),
):
    result = await session.execute(select(User).where(User.id == user_id))
    user_db = result.scalar_one_or_none()

    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    if user_db.id != current_user.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Access denied',
        )

    old_data = UserPublic.model_validate(user_db).model_dump(mode='json')

    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Invalid file format. Use PNG or JPG',
        )

    if user_db.icon_id:
        old_icon = await session.get(UserImage, user_db.icon_id)
        if old_icon:
            await storage.delete(old_icon.file_path)
            await session.delete(old_icon)

    unique_filename = f'{uuid4()}_{file.filename}'
    file_path = await storage.save(file, unique_filename)

    user_image = UserImage(
        user_id=current_user.id,
        type='ICON',
        file_path=file_path,
    )
    session.add(user_image)
    await session.flush()

    user_db.icon_id = user_image.id

    new_data = UserPublic.model_validate(user_db).model_dump(mode='json')
    new_data['icon'] = UserImagePublic.model_validate(user_image).model_dump(
        mode='json'
    )

    user_db.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=user_db.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()

    return Message(message='Icon updated successfully')


@router.get('/', response_model=UserList)
async def read_users(
    session: Session, filters: Annotated[UserFilter, Depends()]
):
    query = (
        select(User)
        .where(User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    )

    if filters.unit_id:
        query = query.where(User.unit_id == filters.unit_id)

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    users = result.all()

    return {'users': users}


@router.get('/my', response_model=UserPublic)
async def read_me(current_user: CurrentUser):
    return current_user


@router.get('/{user_id}/', response_model=UserPublic)
async def read_user(user_id: UUID, session: Session):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )
    return db_user


@router.put('/', response_model=UserPublic)
async def update_user(
    user_update: UserUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, user_update.id)

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

    conflict_user = await session.scalar(
        select(User).where(
            User.deleted_at.is_(None),
            User.id != user_update.id,
            or_(
                User.email == user_update.email,
                User.phone_number == user_update.phone_number,
            ),
        )
    )

    if conflict_user:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )

    db_user.username = user_update.username
    db_user.email = user_update.email
    db_user.phone_number = user_update.phone_number

    if is_admin:
        db_user.access_level = user_update.access_level
        db_user.unit_id = user_update.unit_id
    elif not is_admin and (
        db_user.access_level != user_update.access_level
        or db_user.unit_id != user_update.unit_id
    ):
        pass

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


@router.put('/password', response_model=Message, include_in_schema=False)
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


@router.delete(
    '/{user_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_user(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    old_data = UserPublic.model_validate(db_user).model_dump(mode='json')

    db_user.set_deletion_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=User.__tablename__,
        record_id=db_user.id,
        old_data=old_data,
    )

    await session.commit()


@router.delete('/{user_id}/icon', response_model=Message)
async def delete_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
):
    user_db = await session.get(User, user_id)
    if not user_db:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='User not found',
        )

    if user_db.id != current_user.id:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='Access denied',
        )

    if not user_db.icon_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Icon not found',
        )

    old_data = UserPublic.model_validate(user_db).model_dump(mode='json')

    user_image = await session.get(UserImage, user_db.icon_id)

    if user_image:
        await storage.delete(user_image.file_path)
        await session.delete(user_image)

    user_db.icon_id = None

    new_data = UserPublic.model_validate(user_db).model_dump(mode='json')

    user_db.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=User.__tablename__,
        record_id=user_db.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()

    return Message(message='Icon successfully deleted!')


@router.post('/{user_id}/test-whatsapp', response_model=Message)
async def test_whatsapp(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_user = await session.get(User, user_id)

    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    is_owner = db_user.id == current_user.id
    is_admin = current_user.access_level == AccessType.ADMIN

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail='You are not authorized to test this number',
        )

    if not db_user.phone_number:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='User has no phone number registered',
        )

    result = await notification_service.publish_test_whatsapp_notification(
        db_user, router.broker
    )

    if result['status'] == 'error':
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=result['detail']
        )

    return Message(
        message='Test message sent to WhatsApp queue. Check your device.'
    )


@router.post(
    '/forgot-password', status_code=HTTPStatus.OK, include_in_schema=False
)
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


@router.post(
    '/reset-password', status_code=HTTPStatus.OK, include_in_schema=False
)
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
