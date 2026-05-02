import re
from http import HTTPStatus
from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import CurrentUser
from iaEditais.models import (
    Bundle,
    BundleDocument,
    BundleDocumentTypification,
    Document,
    DocumentHistory,
)
from iaEditais.repositories import bundle_repo, doc_repo
from iaEditais.schemas import (
    BundleCreate,
    BundleDocumentCreate,
    BundleFilter,
    BundleGenerateDocsRequest,
    BundlePublic,
    BundleUpdate,
    DocumentProcessingStatus,
    DocumentStatus,
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


async def generate_docs_from_bundle(
    session: AsyncSession,
    current_user: CurrentUser,
    bundle_id: UUID,
    data: BundleGenerateDocsRequest,
) -> List[Document]:
    bundle = await bundle_repo.get_bundle_with_relations(session, bundle_id)
    if not bundle:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Bundle not found.'
        )

    created_docs = []

    for b_doc in bundle.documents:
        doc_name = f'{b_doc.name} - {data.base_name}'

        safe_b_doc_name = re.sub(r'[^A-Za-z0-9]', '', b_doc.name).upper()
        doc_identifier = f'{data.base_identifier}-{safe_b_doc_name}'

        existing_doc = await doc_repo.get_by_identifier(
            session, doc_identifier
        )
        if existing_doc:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f'Doc with identifier "{doc_identifier}" already exists.',
            )

        db_doc = Document(
            name=doc_name,
            description=data.base_description,
            identifier=doc_identifier,
            unit_id=current_user.unit_id,
            processing_status=DocumentProcessingStatus.IDLE,
            bundle_id=bundle.id,
        )
        db_doc.set_creation_audit(current_user.id)
        doc_repo.add_document(session, db_doc)
        await session.flush()

        history = DocumentHistory(
            document_id=db_doc.id,
            status=DocumentStatus.PENDING.value,
        )
        history.set_creation_audit(current_user.id)
        doc_repo.add_history(session, history)

        if b_doc.typifications:
            db_doc.typifications = list(b_doc.typifications)

        await audit_service.register_action(
            session=session,
            user_id=current_user.id,
            action='CREATE',
            table_name=Document.__tablename__,
            record_id=db_doc.id,
            old_data=None,
        )

        created_docs.append(db_doc)

    await session.commit()

    for doc in created_docs:
        await session.refresh(doc)

    return created_docs
