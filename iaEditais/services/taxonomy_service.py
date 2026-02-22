from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Taxonomy, TaxonomySource
from iaEditais.repositories import taxonomy_repo
from iaEditais.schemas import (
    TaxonomyCreate,
    TaxonomyPublic,
    TaxonomyUpdate,
)
from iaEditais.schemas.taxonomy import TaxonomyFilter
from iaEditais.services import audit_service


async def create_taxonomy(
    session: AsyncSession, user_id: UUID, data: TaxonomyCreate
) -> Taxonomy:
    # Verifica duplicidade
    conflict = await taxonomy_repo.get_conflict(
        session, data.title, data.typification_id
    )
    if conflict:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Taxonomy title already exists for this typification',
        )

    # Verifica Tipificação
    typification = await taxonomy_repo.get_typification(
        session, data.typification_id
    )
    if not typification or typification.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Typification not found',
        )

    db_taxonomy = Taxonomy(
        title=data.title,
        description=data.description,
        typification_id=data.typification_id,
    )
    db_taxonomy.set_creation_audit(user_id)

    taxonomy_repo.add_taxonomy(session, db_taxonomy)
    await session.flush()

    # Processa Sources (Many-to-Many manual na criação para setar created_by)
    if data.source_ids:
        sources = await taxonomy_repo.get_sources_by_ids(
            session, data.source_ids
        )
        existing_source_ids = {s.id for s in sources}

        if len(existing_source_ids) != len(data.source_ids):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='One or more sources not found',
            )

        for source_id in data.source_ids:
            association_entry = TaxonomySource(
                taxonomy_id=db_taxonomy.id,
                source_id=source_id,
                created_by=user_id,
            )
            taxonomy_repo.add_taxonomy_source(session, association_entry)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Taxonomy.__tablename__,
        record_id=db_taxonomy.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_taxonomy)
    return db_taxonomy


async def get_taxonomies(
    session: AsyncSession, filters: TaxonomyFilter
) -> list[Taxonomy]:
    return await taxonomy_repo.list_all(session, filters)


async def get_taxonomy_by_id(
    session: AsyncSession, taxonomy_id: UUID
) -> Taxonomy:
    taxonomy = await taxonomy_repo.get_by_id(session, taxonomy_id)
    if not taxonomy or taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )
    return taxonomy


async def update_taxonomy(
    session: AsyncSession, user_id: UUID, data: TaxonomyUpdate
) -> Taxonomy:
    db_taxonomy = await taxonomy_repo.get_by_id(session, data.id)

    if not db_taxonomy or db_taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    old_data = TaxonomyPublic.model_validate(db_taxonomy).model_dump(
        mode='json'
    )

    title_changed = data.title != db_taxonomy.title
    typification_changed = data.typification_id != db_taxonomy.typification_id

    if title_changed or typification_changed:
        conflict = await taxonomy_repo.get_conflict(
            session, data.title, data.typification_id, exclude_id=data.id
        )
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Taxonomy title already exists for this typification',
            )

    if typification_changed:
        typification = await taxonomy_repo.get_typification(
            session, data.typification_id
        )
        if not typification or typification.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Typification not found',
            )

    # Atualiza Sources (Via relacionamento SQLAlchemy)
    if data.source_ids:
        sources = await taxonomy_repo.get_sources_by_ids(
            session, data.source_ids
        )
        # Note: A atualização via relacionamento direto substitui a lista.
        # Se for necessário setar 'created_by' em novos links, o modelo ORM deve tratar isso
        # ou deve-se fazer manualmente como no create.
        # Mantendo a lógica original do router que usava atribuição direta.
        db_taxonomy.sources = list(sources)
    else:
        db_taxonomy.sources = []

    db_taxonomy.title = data.title
    db_taxonomy.description = data.description
    db_taxonomy.typification_id = data.typification_id

    new_data = TaxonomyPublic.model_validate(db_taxonomy).model_dump(
        mode='json'
    )
    db_taxonomy.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Taxonomy.__tablename__,
        record_id=db_taxonomy.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_taxonomy)
    return db_taxonomy


async def delete_taxonomy(
    session: AsyncSession, user_id: UUID, taxonomy_id: UUID
) -> None:
    db_taxonomy = await taxonomy_repo.get_by_id(session, taxonomy_id)

    if not db_taxonomy or db_taxonomy.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Taxonomy not found',
        )

    old_data = TaxonomyPublic.model_validate(db_taxonomy).model_dump(
        mode='json'
    )
    db_taxonomy.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Taxonomy.__tablename__,
        record_id=db_taxonomy.id,
        old_data=old_data,
    )

    await session.commit()
