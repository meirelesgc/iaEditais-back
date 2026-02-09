from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import (
    Source,
    Taxonomy,
    TaxonomySource,
    Typification,
)
from iaEditais.schemas import (
    FilterPage,
    TaxonomyCreate,
    TaxonomyList,
    TaxonomyPublic,
    TaxonomyUpdate,
)
from iaEditais.services import audit_service

router = APIRouter(
    prefix='/taxonomy',
    tags=['árvore de verificação, taxonomias'],
)


@router.post('', status_code=HTTPStatus.CREATED, response_model=TaxonomyPublic)
async def create_taxonomy(
    taxonomy: TaxonomyCreate,
    session: Session,
    current_user: CurrentUser,
):
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

    db_taxonomy.set_creation_audit(current_user.id)

    session.add(db_taxonomy)

    await session.flush()

    if taxonomy.source_ids:
        source_check = await session.scalars(
            select(Source.id).where(Source.id.in_(taxonomy.source_ids))
        )
        existing_source_ids = set(source_check.all())

        if len(existing_source_ids) != len(taxonomy.source_ids):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='One or more sources not found',
            )

        for source_id in taxonomy.source_ids:
            association_entry = TaxonomySource(
                taxonomy_id=db_taxonomy.id,
                source_id=source_id,
                created_by=current_user.id,
            )
            session.add(association_entry)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Taxonomy.__tablename__,
        record_id=db_taxonomy.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_taxonomy)

    return db_taxonomy


@router.get('', response_model=TaxonomyList)
async def read_taxonomies(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Taxonomy)
        .where(Taxonomy.deleted_at.is_(None))
        .order_by(Taxonomy.created_at.desc())
        .offset(filters.offset)
        .limit(filters.limit)
    )
    taxonomies = query.all()
    return {'taxonomies': taxonomies}


@router.get('/{taxonomy_id}', response_model=TaxonomyPublic)
async def read_taxonomy(taxonomy_id: UUID, session: Session):
    result = await session.execute(
        select(Taxonomy).where(Taxonomy.id == taxonomy_id)
    )
    taxonomy = result.scalar_one_or_none()

    if not taxonomy or taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    return taxonomy


@router.put('', response_model=TaxonomyPublic)
async def update_taxonomy(
    taxonomy: TaxonomyUpdate,
    session: Session,
    current_user: CurrentUser,
):
    db_taxonomy = await session.get(Taxonomy, taxonomy.id)

    if not db_taxonomy or db_taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    old_data = TaxonomyPublic.model_validate(db_taxonomy).model_dump(
        mode='json'
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

    if taxonomy.source_ids:
        sources = await session.scalars(
            select(Source).where(Source.id.in_(taxonomy.source_ids))
        )
        db_taxonomy.sources = sources.all()
    else:
        db_taxonomy.sources = []

    db_taxonomy.title = taxonomy.title
    db_taxonomy.description = taxonomy.description
    db_taxonomy.typification_id = taxonomy.typification_id

    new_data = TaxonomyPublic.model_validate(db_taxonomy).model_dump(
        mode='json'
    )

    db_taxonomy.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Taxonomy.__tablename__,
        record_id=db_taxonomy.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_taxonomy)
    return db_taxonomy


@router.delete(
    '/{taxonomy_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_taxonomy(
    taxonomy_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    db_taxonomy = await session.get(Taxonomy, taxonomy_id)

    if not db_taxonomy or db_taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    old_data = TaxonomyPublic.model_validate(db_taxonomy).model_dump(
        mode='json'
    )

    db_taxonomy.set_deletion_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Taxonomy.__tablename__,
        record_id=db_taxonomy.id,
        old_data=old_data,
    )

    await session.commit()

    return {'message': 'Taxonomy deleted'}
