from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import CurrentUser
from iaEditais.models import Document, DocumentHistory
from iaEditais.repositories import doc_repo
from iaEditais.schemas import (
    DocumentCreate,
    DocumentFilter,
    DocumentProcessingStatus,
    DocumentPublic,
    DocumentStatus,
    DocumentUpdate,
)
from iaEditais.schemas.typification import TypificationList
from iaEditais.schemas.user import UserList
from iaEditais.services import audit_service


async def create_doc(
    session: AsyncSession, current_user: CurrentUser, data: DocumentCreate
) -> Document:
    # Validação de unicidade
    existing_doc = await doc_repo.get_by_identifier(session, data.identifier)
    if existing_doc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f'Doc with identifier "{data.identifier}" already exists.',
        )

    db_doc = Document(
        name=data.name,
        description=data.description,
        identifier=data.identifier,
        unit_id=current_user.unit_id,
        processing_status=DocumentProcessingStatus.IDLE,
    )
    db_doc.set_creation_audit(current_user.id)
    doc_repo.add_document(session, db_doc)
    await session.flush()

    # Histórico inicial
    history = DocumentHistory(
        document_id=db_doc.id,
        status=DocumentStatus.PENDING.value,
    )
    history.set_creation_audit(current_user.id)
    doc_repo.add_history(session, history)

    # Relacionamentos Many-to-Many
    if data.typification_ids:
        typifications = await doc_repo.get_typifications_by_ids(
            session, data.typification_ids
        )
        db_doc.typifications = list(typifications)

    if data.editors_ids:
        editors = await doc_repo.get_users_by_ids(session, data.editors_ids)
        db_doc.editors = list(editors)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=Document.__tablename__,
        record_id=db_doc.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def get_docs(
    session: AsyncSession, filters: DocumentFilter
) -> list[Document]:
    return await doc_repo.list_all(session, filters)


async def get_doc_by_id(session: AsyncSession, doc_id: UUID) -> Document:
    doc = await doc_repo.get_by_id(session, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )
    return doc


async def update_doc(
    session: AsyncSession, current_user: CurrentUser, data: DocumentUpdate
) -> Document:
    db_doc = await get_doc_by_id(session, data.id)

    old_data = DocumentPublic.model_validate(db_doc).model_dump(mode='json')

    # Verifica conflito de identificador
    conflict = await doc_repo.get_by_identifier(
        session, data.identifier, exclude_id=data.id
    )
    if conflict:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=f'Doc with identifier "{data.identifier}" already exists.',
        )

    db_doc.name = data.name
    db_doc.description = data.description
    db_doc.identifier = data.identifier

    new_data = DocumentPublic.model_validate(db_doc).model_dump(mode='json')

    # Atualiza relacionamentos
    if data.typification_ids is not None:
        typifications = await doc_repo.get_typifications_by_ids(
            session, data.typification_ids
        )
        typ_list = list(typifications)
        db_doc.typifications = typ_list
        new_data['typifications'] = TypificationList.model_validate({
            'typifications': typ_list
        }).model_dump(mode='json')

    if data.editors_ids is not None:
        editors = await doc_repo.get_users_by_ids(session, data.editors_ids)
        user_list = list(editors)
        db_doc.editors = user_list
        new_data['editors'] = UserList.model_validate({
            'users': user_list
        }).model_dump(mode='json')

    db_doc.set_update_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='UPDATE',
        table_name=Document.__tablename__,
        record_id=db_doc.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def toggle_archive(
    session: AsyncSession, current_user: CurrentUser, doc_id: UUID
) -> Document:
    db_doc = await get_doc_by_id(session, doc_id)

    old_data = DocumentPublic.model_validate(db_doc).model_dump(mode='json')

    db_doc.is_archived = not db_doc.is_archived
    db_doc.set_update_audit(current_user.id)

    action = 'ARCHIVE' if db_doc.is_archived else 'UPDATE'

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action=action,
        table_name=Document.__tablename__,
        record_id=db_doc.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


async def delete_doc(
    session: AsyncSession, current_user: CurrentUser, doc_id: UUID
) -> None:
    db_doc = await get_doc_by_id(session, doc_id)

    old_data = DocumentPublic.model_validate(db_doc).model_dump(mode='json')
    db_doc.set_deletion_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=Document.__tablename__,
        record_id=db_doc.id,
        old_data=old_data,
    )

    await session.commit()
