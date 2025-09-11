from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Taxonomy, Typification
from iaEditais.schemas import (
    FilterPage,
    Message,
    TaxonomyCreate,
    TaxonomyList,
    TaxonomyPublic,
    TaxonomyUpdate,
)

router = APIRouter(
    prefix='/taxonomy',
    tags=['árvore de verificação, taxonomias'],
)


Session = Annotated[AsyncSession, Depends(get_session)]


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TaxonomyPublic,
)
async def create_taxonomy(taxonomy: TaxonomyCreate, session: Session):
    db_taxonomy = await session.scalar(
        select(Taxonomy).where(
            Taxonomy.deleted_at.is_(None),
            Taxonomy.title == taxonomy.title,
        )
    )

    if db_taxonomy:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Taxonomy title already exists',
        )

    typification = await session.get(Typification, taxonomy.typification_id)
    if not typification or typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    db_taxonomy = Taxonomy(
        title=taxonomy.title,
        description=taxonomy.description,
        typification_id=taxonomy.typification_id,
    )

    session.add(db_taxonomy)
    await session.commit()
    await session.refresh(db_taxonomy, attribute_names=['typification'])

    return db_taxonomy


@router.get('/', response_model=TaxonomyList)
async def read_taxonomies(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Taxonomy)
        .where(Taxonomy.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )
    taxonomies = query.all()
    return {'taxonomies': taxonomies}


@router.get('/{taxonomy_id}', response_model=TaxonomyPublic)
async def read_taxonomy(taxonomy_id: UUID, session: Session):
    taxonomy = await session.get(Taxonomy, taxonomy_id)

    if not taxonomy or taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    return taxonomy


@router.put('/', response_model=TaxonomyPublic)
async def update_taxonomy(taxonomy: TaxonomyUpdate, session: Session):
    db_taxonomy = await session.get(Taxonomy, taxonomy.id)

    if not db_taxonomy or db_taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    if taxonomy.title != db_taxonomy.title:
        db_taxonomy_same_title = await session.scalar(
            select(Taxonomy).where(
                Taxonomy.deleted_at.is_(None),
                Taxonomy.title == taxonomy.title,
                Taxonomy.id != taxonomy.id,
            )
        )
        if db_taxonomy_same_title:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Taxonomy title already exists',
            )

    if taxonomy.typification_id != db_taxonomy.typification_id:
        typification = await session.get(
            Typification, taxonomy.typification_id
        )
        if not typification or typification.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Typification not found',
            )

    db_taxonomy.title = taxonomy.title
    db_taxonomy.description = taxonomy.description
    db_taxonomy.typification_id = taxonomy.typification_id

    try:
        await session.commit()
        await session.refresh(
            db_taxonomy, attribute_names=['typification', 'updated_at']
        )
        return db_taxonomy
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Taxonomy title already exists',
        )


@router.delete('/{taxonomy_id}', response_model=Message)
async def delete_taxonomy(taxonomy_id: UUID, session: Session):
    db_taxonomy = await session.get(Taxonomy, taxonomy_id)

    if not db_taxonomy or db_taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    db_taxonomy.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    return {'message': 'Taxonomy deleted'}
