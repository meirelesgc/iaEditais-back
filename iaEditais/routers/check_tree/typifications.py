from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import (
    Source,
    Typification,
    TypificationSource,
)
from iaEditais.schemas import (
    FilterPage,
    TypificationCreate,
    TypificationList,
    TypificationPublic,
    TypificationUpdate,
)

router = APIRouter(
    prefix='/typification',
    tags=['árvore de verificação, tipificações'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TypificationPublic,
)
async def create_typification(
    typification: TypificationCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_typification = await session.scalar(
        select(Typification).where(
            Typification.deleted_at.is_(None),
            Typification.name == typification.name,
        )
    )

    if db_typification:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Typification name already exists',
        )

    db_typification = Typification(
        name=typification.name,
        created_by=current_user.id,
    )
    session.add(db_typification)

    if typification.source_ids:
        source_check = await session.scalars(
            select(Source.id).where(Source.id.in_(typification.source_ids))
        )
        existing_source_ids = set(source_check.all())

        if len(existing_source_ids) != len(typification.source_ids):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='One or more sources not found',
            )

        for source_id in typification.source_ids:
            association_entry = TypificationSource(
                typification_id=db_typification.id,
                source_id=source_id,
                created_by=current_user.id,
            )
            session.add(association_entry)

    await session.commit()
    await session.refresh(db_typification)

    return db_typification


@router.get('/', response_model=TypificationList)
async def read_typifications(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Typification)
        .where(Typification.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )
    typifications = query.all()
    return {'typifications': typifications}


@router.get('/{typification_id}', response_model=TypificationPublic)
async def read_typification(typification_id: UUID, session: Session):
    typification = await session.get(Typification, typification_id)

    if not typification or typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    return typification


@router.put('/', response_model=TypificationPublic)
async def update_typification(
    typification: TypificationUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_typification = await session.get(Typification, typification.id)

    if not db_typification or db_typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    db_typification_same_name = await session.scalar(
        select(Typification).where(
            Typification.deleted_at.is_(None),
            Typification.name == typification.name,
            Typification.id != typification.id,
        )
    )

    if db_typification_same_name:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Typification name already exists',
        )

    db_typification.name = typification.name
    db_typification.updated_by = current_user.id

    if typification.source_ids:
        sources = await session.scalars(
            select(Source).where(Source.id.in_(typification.source_ids))
        )
        db_typification.sources = sources.all()
    else:
        db_typification.sources = []

    await session.commit()
    await session.refresh(db_typification)
    return db_typification


@router.delete(
    '/{typification_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_typification(
    typification_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_typification = await session.get(Typification, typification_id)

    if not db_typification or db_typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    db_typification.deleted_at = datetime.now(timezone.utc)
    db_typification.deleted_by = current_user.id
    await session.commit()

    return {'message': 'Typification deleted'}
