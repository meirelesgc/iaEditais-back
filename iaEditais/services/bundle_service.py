from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Bundle, BundleDocument, BundleDocumentTypification
from iaEditais.repositories import bundle_repo
from iaEditais.schemas.bundle import (
    BundleCreate,
    BundleDocumentCreate,
    BundleFilter,
    BundlePublic,
    BundleUpdate,
)
from iaEditais.services import audit_service


async def create_bundle(
    session: AsyncSession, user_id: UUID, data: BundleCreate
) -> Bundle:
    existing_bundle = await bundle_repo.get_by_name(session, data.name)
    if existing_bundle:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Bundle name already exists',
        )

    db_bundle = Bundle(name=data.name)
    db_bundle.set_creation_audit(user_id)

    bundle_repo.add_bundle(session, db_bundle)
    await session.flush()

    created_docs = []

    for doc_data in data.documents:
        db_doc = BundleDocument(name=doc_data.name, bundle_id=db_bundle.id)
        db_doc.set_creation_audit(user_id)
        bundle_repo.add_bundle_document(session, db_doc)
        await session.flush()

        created_docs.append(db_doc)

        if doc_data.typification_ids:
            typifications = await bundle_repo.get_typifications_by_ids(
                session, doc_data.typification_ids
            )
            existing_typification_ids = {t.id for t in typifications}

            if len(existing_typification_ids) != len(
                doc_data.typification_ids
            ):
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND,
                    detail='One or more typifications not found',
                )

            for typ_id in doc_data.typification_ids:
                association_entry = BundleDocumentTypification(
                    bundle_document_id=db_doc.id,
                    typification_id=typ_id,
                    created_by=user_id,
                )
                bundle_repo.add_bundle_document_typification(
                    session, association_entry
                )

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Bundle.__tablename__,
        record_id=db_bundle.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_bundle)

    for doc in created_docs:
        await session.refresh(doc)

    return db_bundle


async def get_bundles(
    session: AsyncSession, filters: BundleFilter
) -> list[Bundle]:
    return await bundle_repo.list_all(session, filters)


async def get_bundle_by_id(session: AsyncSession, bundle_id: UUID) -> Bundle:
    bundle = await bundle_repo.get_by_id(session, bundle_id)
    if not bundle or bundle.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Bundle not found',
        )
    return bundle


async def update_bundle(
    session: AsyncSession, user_id: UUID, data: BundleUpdate
) -> Bundle:
    db_bundle = await bundle_repo.get_by_id(session, data.id)

    if not db_bundle or db_bundle.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Bundle not found',
        )

    old_data = BundlePublic.model_validate(db_bundle).model_dump(mode='json')

    if data.name and data.name != db_bundle.name:
        conflict = await bundle_repo.get_by_name(
            session, data.name, exclude_id=data.id
        )
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Bundle name already exists',
            )
        db_bundle.name = data.name

    db_bundle.set_update_audit(user_id)
    new_data = BundlePublic.model_validate(db_bundle).model_dump(mode='json')

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Bundle.__tablename__,
        record_id=db_bundle.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_bundle)
    return db_bundle


async def delete_bundle(
    session: AsyncSession, user_id: UUID, bundle_id: UUID
) -> None:
    db_bundle = await bundle_repo.get_by_id(session, bundle_id)

    if not db_bundle or db_bundle.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Bundle not found',
        )

    old_data = BundlePublic.model_validate(db_bundle).model_dump(mode='json')
    db_bundle.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Bundle.__tablename__,
        record_id=db_bundle.id,
        old_data=old_data,
    )

    await session.commit()


async def add_document(
    session: AsyncSession,
    user_id: UUID,
    bundle_id: UUID,
    data: BundleDocumentCreate,
) -> Bundle:
    db_bundle = await bundle_repo.get_by_id(session, bundle_id)

    if not db_bundle or db_bundle.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Bundle not found',
        )

    db_doc = BundleDocument(name=data.name, bundle_id=db_bundle.id)
    db_doc.set_creation_audit(user_id)
    bundle_repo.add_bundle_document(session, db_doc)
    await session.flush()

    if data.typification_ids:
        typifications = await bundle_repo.get_typifications_by_ids(
            session, data.typification_ids
        )
        existing_typification_ids = {t.id for t in typifications}

        if len(existing_typification_ids) != len(data.typification_ids):
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='One or more typifications not found',
            )

        for typ_id in data.typification_ids:
            association_entry = BundleDocumentTypification(
                bundle_document_id=db_doc.id,
                typification_id=typ_id,
                created_by=user_id,
            )
            bundle_repo.add_bundle_document_typification(
                session, association_entry
            )

    db_bundle.set_update_audit(user_id)

    await session.commit()
    await session.refresh(db_bundle)
    await session.refresh(db_doc)

    return db_bundle


async def remove_document(
    session: AsyncSession, user_id: UUID, bundle_id: UUID, document_id: UUID
) -> None:
    db_bundle = await bundle_repo.get_by_id(session, bundle_id)
    if not db_bundle or db_bundle.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Bundle not found',
        )

    db_doc = await bundle_repo.get_document_by_id(session, document_id)
    if not db_doc or db_doc.bundle_id != bundle_id or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Bundle document not found',
        )

    db_doc.set_deletion_audit(user_id)
    db_bundle.set_update_audit(user_id)
    await session.commit()
