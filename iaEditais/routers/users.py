from datetime import datetime, timezone
from http import HTTPStatus
from secrets import token_hex
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_, select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.core.security import get_password_hash
from iaEditais.models import User, UserImage
from iaEditais.schemas import (
    UserCreate,
    UserFilter,
    UserList,
    UserPublic,
    UserUpdate,
)
from iaEditais.schemas.common import Message
from iaEditais.services import storage_service

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'

router = APIRouter(prefix='/user', tags=['operações de sistema, usuário'])


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
    if not user.password:
        user.password = token_hex(256)
    hashed_password = get_password_hash(user.password)

    db_user = User(
        username=user.username,
        email=user.email,
        phone_number=user.phone_number,
        password=hashed_password,
        access_level=user.access_level,
        unit_id=user.unit_id,
    )

    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)

    return db_user


@router.post('/{user_id}/icon', response_model=Message)
async def add_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
    file: UploadFile = File(...),
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
            detail='Access denieds',
        )

    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(
            status_code=400,
            detail='Invalid file format. Use PNG or JPG',
        )

    file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)
    user_image = UserImage(
        user_id=current_user.id,
        type='ICON',
        file_path=file_path,
    )
    session.add(user_image)
    await session.commit()
    await session.refresh(user_image)

    return Message(message='Success')


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
    db_user.access_level = user_update.access_level
    db_user.unit_id = user_update.unit_id
    db_user.updated_by = current_user.id

    if user_update.password:
        db_user.password = get_password_hash(user_update.password)

    await session.commit()
    await session.refresh(db_user)

    return db_user


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

    db_user.deleted_at = datetime.now(timezone.utc)
    db_user.deleted_by = current_user.id
    await session.commit()

    return {'message': 'User deleted'}


@router.delete('/{user_id}/icon', response_model=Message)
async def delete_icon(
    user_id: UUID,
    session: Session,
    current_user: CurrentUser,
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

    user_image = await session.execute(
        select(UserImage).where(
            UserImage.user_id == current_user.id,
            UserImage.type == 'ICON',
        )
    )
    user_image = user_image.scalar_one_or_none()

    if not user_image:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Icon not found',
        )

    await storage_service.delete_file(user_image.file_path)

    await session.delete(user_image)
    await session.commit()

    return Message(message='Icon successfully deleted!')
