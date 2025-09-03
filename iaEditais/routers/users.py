from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import User
from iaEditais.schemas import (
    FilterPage,
    Message,
    UserCreate,
    UserList,
    UserPublic,
    UserUpdate,
)
from iaEditais.security import get_password_hash

router = APIRouter(prefix='/user', tags=['operações de sistema, usuário'])
Session = Annotated[AsyncSession, Depends(get_session)]


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


@router.get('/', response_model=UserList)
async def read_users(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(User)
        .where(User.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )
    users = query.all()
    return {'users': users}


# WIP: ENDPOINT MY-SELF / MY


@router.get('/{user_id}/', response_model=UserPublic)
async def read_user(user_id: UUID, session: Session):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )
    return db_user


@router.put('/', response_model=UserPublic)
async def update_user(user_update: UserUpdate, session: Session):
    db_user = await session.get(User, user_update.id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    db_user.username = user_update.username
    db_user.email = user_update.email
    db_user.phone_number = user_update.phone_number
    db_user.access_level = user_update.access_level
    db_user.unit_id = user_update.unit_id

    if user_update.password:
        db_user.password = get_password_hash(user_update.password)

    try:
        await session.commit()
        await session.refresh(db_user)
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Email or phone number already registered',
        )

    return db_user


@router.delete('/{user_id}/', response_model=Message)
async def delete_user(user_id: UUID, session: Session):
    db_user = await session.get(User, user_id)
    if not db_user or db_user.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='User not found'
        )

    db_user.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    return {'message': 'User deleted'}
