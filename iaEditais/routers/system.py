from datetime import datetime
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import (
    SystemSetting,
)
from iaEditais.schemas import (
    FilterPage,
    Message,
    SystemSettingCreate,
    SystemSettingList,
    SystemSettingPublic,
    SystemSettingUpdate,
)

router = APIRouter(prefix='/system-settings', tags=['system settings'])


@router.post(
    '', status_code=HTTPStatus.CREATED, response_model=SystemSettingPublic
)
async def create_setting(
    setting: SystemSettingCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_setting = await session.scalar(
        select(SystemSetting).where(SystemSetting.key == setting.key)
    )

    if db_setting and not db_setting.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='A setting with this key already exists',
        )

    if db_setting and db_setting.deleted_at:
        db_setting.value = setting.value
        db_setting.description = setting.description
        db_setting.deleted_at = None
        db_setting.updated_at = datetime.now()
    else:
        db_setting = SystemSetting(**setting.model_dump())

    session.add(db_setting)
    await session.commit()
    await session.refresh(db_setting)

    return db_setting


@router.get('', response_model=SystemSettingList)
async def read_settings(
    session: Session,
    current_user: CurrentUser,
    filter_page: Annotated[FilterPage, Depends()],
):
    query = (
        select(SystemSetting)
        .where(SystemSetting.deleted_at.is_(None))
        .order_by(SystemSetting.key)
        .offset(filter_page.offset)
        .limit(filter_page.limit)
    )
    result = await session.scalars(query)
    settings = result.all()

    return {'settings': settings}


@router.put('/{key}', response_model=SystemSettingPublic)
async def update_setting(
    key: str,
    setting_update: SystemSettingUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_setting = await session.scalar(
        select(SystemSetting).where(
            SystemSetting.key == key, SystemSetting.deleted_at.is_(None)
        )
    )

    if not db_setting:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Setting not found',
        )

    update_data = setting_update.model_dump(exclude_unset=True)

    if not update_data:
        return db_setting

    for field, value in update_data.items():
        setattr(db_setting, field, value)

    session.add(db_setting)
    await session.commit()
    await session.refresh(db_setting)

    return db_setting


@router.delete('/{key}', response_model=Message)
async def delete_setting(
    key: str, session: Session, current_user: CurrentUser
):
    db_setting = await session.scalar(
        select(SystemSetting).where(SystemSetting.key == key)
    )

    if not db_setting or db_setting.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Setting not found',
        )

    db_setting.deleted_at = datetime.now()
    session.add(db_setting)
    await session.commit()

    return {'message': 'Setting successfully deactivated'}


@router.get('/{identifier}', response_model=SystemSettingPublic)
async def read_setting(
    identifier: str,
    session: Session,
    current_user: CurrentUser,
):
    db_setting = await session.scalar(
        select(SystemSetting).where(
            SystemSetting.key == identifier,
            SystemSetting.deleted_at.is_(None),
        )
    )

    if not db_setting:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Setting not found',
        )

    return db_setting
