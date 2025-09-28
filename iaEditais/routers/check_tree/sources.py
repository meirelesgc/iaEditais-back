from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Source
from iaEditais.schemas import (
    FilterPage,
    SourceCreate,
    SourceList,
    SourcePublic,
    SourceUpdate,
)

router = APIRouter(prefix='/source', tags=['árvore de verificação, fontes'])


@router.post('/', status_code=HTTPStatus.CREATED, response_model=SourcePublic)
async def create_source(
    source: SourceCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_source = await session.scalar(
        select(Source).where(
            Source.deleted_at.is_(None), Source.name == source.name
        )
    )

    if db_source:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Source name already exists',
        )

    db_source = Source(
        name=source.name,
        description=source.description,
        created_by=current_user.id,
    )

    session.add(db_source)
    await session.commit()
    await session.refresh(
        db_source,
        attribute_names=['typifications'],
    )

    return db_source


@router.get('/', response_model=SourceList)
async def read_sources(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Source)
        .where(Source.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )

    sources = query.all()
    return {'sources': sources}


@router.get('/{source_id}', response_model=SourcePublic)
async def read_source(source_id: UUID, session: Session):
    source = await session.get(Source, source_id)

    if not source or source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    return source


@router.put('/', response_model=SourcePublic)
async def update_source(
    source: SourceUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_source = await session.get(Source, source.id)

    if not db_source or db_source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    db_source_same_name = await session.scalar(
        select(Source).where(
            Source.deleted_at.is_(None), Source.name == source.name
        )
    )

    if db_source_same_name:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Source name already exists',
        )

    db_source.name = source.name
    db_source.description = source.description
    db_source.updated_by = current_user.id

    await session.commit()
    await session.refresh(
        db_source,
        attribute_names=['typifications', 'updated_at'],
    )

    return db_source


@router.delete(
    '/{source_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_source(
    source_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_source = await session.get(Source, source_id)

    if not db_source or db_source.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Source not found',
        )

    db_source.deleted_at = datetime.now(timezone.utc)
    db_source.deleted_by = current_user.id
    await session.commit()

    return {'message': 'Source deleted'}
