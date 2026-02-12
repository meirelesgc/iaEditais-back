from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select, true
from sqlalchemy.orm import aliased

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import (
    Document,
    DocumentHistory,
    Typification,
    User,
)
from iaEditais.repositories import util
from iaEditais.schemas import (
    DocumentCreate,
    DocumentFilter,
    DocumentList,
    DocumentProcessingStatus,
    DocumentPublic,
    DocumentStatus,
    DocumentUpdate,
)
from iaEditais.schemas.typification import TypificationList
from iaEditais.schemas.user import UserList
from iaEditais.services import audit_service

router = APIRouter(prefix='/doc', tags=['verificação dos documentos, editais'])


@router.post('', status_code=HTTPStatus.CREATED, response_model=DocumentPublic)
async def create_doc(
    doc: DocumentCreate, session: Session, current_user: CurrentUser
):
    db_doc = await session.scalar(
        select(Document).where(
            Document.identifier == doc.identifier,
        )
    )
    if db_doc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=(f'Doc with identifier "{doc.identifier}" already exists.'),
        )

    db_doc = Document(
        name=doc.name,
        description=doc.description,
        identifier=doc.identifier,
        unit_id=current_user.unit_id,
        processing_status=DocumentProcessingStatus.IDLE,
    )

    db_doc.set_creation_audit(current_user.id)

    session.add(db_doc)

    await session.flush()

    history = DocumentHistory(
        document_id=db_doc.id,
        status=DocumentStatus.PENDING.value,
    )

    history.set_creation_audit(current_user.id)
    session.add(history)

    if doc.typification_ids:
        typifications = await session.scalars(
            select(Typification).where(
                Typification.id.in_(doc.typification_ids)
            )
        )
        db_doc.typifications = [typ for typ in typifications.all()]

    if doc.editors_ids:
        editors = await session.scalars(
            select(User).where(User.id.in_(doc.editors_ids))
        )
        db_doc.editors = [user for user in editors.all()]

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


@router.get('', response_model=DocumentList)
async def read_docs(
    session: Session, filters: Annotated[DocumentFilter, Depends()]
):
    last_history_subq = (
        select(DocumentHistory)
        .where(DocumentHistory.document_id == Document.id)
        .order_by(DocumentHistory.created_at.desc())
        .limit(1)
        .lateral()
    )

    last_history = aliased(DocumentHistory, last_history_subq)

    query = (
        select(Document)
        .join(last_history, true())
        .where(Document.deleted_at.is_(None))
        .order_by(last_history.status.asc(), last_history.created_at.asc())
    )

    if filters.unit_id:
        query = query.where(Document.unit_id == filters.unit_id)

    if filters.archived is not None:
        query = query.where(Document.is_archived == filters.archived)

    if filters.q:
        query = util.apply_text_search(query, Document, filters.q)

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    docs = result.all()

    return {'documents': docs}


@router.get('/{doc_id}', response_model=DocumentPublic)
async def read_doc(doc_id: UUID, session: Session):
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )
    return doc


@router.put('', response_model=DocumentPublic)
async def update_doc(
    doc: DocumentUpdate, session: Session, current_user: CurrentUser
):
    result = await session.execute(
        select(Document).where(Document.id == doc.id)
    )

    db_doc = result.scalar_one_or_none()

    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    old_data = DocumentPublic.model_validate(db_doc).model_dump(mode='json')

    db_doc_conflict = await session.scalar(
        select(Document).where(
            Document.id != doc.id, or_(Document.identifier == doc.identifier)
        )
    )
    if db_doc_conflict:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=(f'Doc with identifier "{doc.identifier}" already exists.'),
        )

    db_doc.name = doc.name
    db_doc.description = doc.description
    db_doc.identifier = doc.identifier

    new_data = DocumentPublic.model_validate(db_doc).model_dump(mode='json')

    if doc.typification_ids is not None:
        typifications = await session.scalars(
            select(Typification).where(
                Typification.id.in_(doc.typification_ids)
            )
        )
        typ_list = [typ for typ in typifications.all()]
        db_doc.typifications = typ_list
        new_data['typifications'] = TypificationList.model_validate({
            'typifications': typ_list
        }).model_dump(mode='json')
    if doc.editors_ids:
        editors = await session.scalars(
            select(User).where(User.id.in_(doc.editors_ids))
        )
        user_list = [user for user in editors.all()]
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


@router.put('/{document_id}/toggle-archive', response_model=DocumentPublic)
async def toggle_archive(
    document_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    query = select(Document).where(
        Document.id == document_id, Document.deleted_at.is_(None)
    )
    doc = await session.scalar(query)
    if not doc:
        raise HTTPException(status_code=404, detail='Documento não encontrado')

    old_data = DocumentPublic.model_validate(doc).model_dump(mode='json')

    doc.is_archived = not doc.is_archived

    doc.set_update_audit(current_user.id)

    action = 'ARCHIVE' if doc.is_archived else 'UPDATE'
    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action=action,
        table_name=Document.__tablename__,
        record_id=doc.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(doc)

    return doc


@router.delete(
    '/{doc_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_doc(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    db_doc = result.scalar_one_or_none()

    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

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

    return {'message': 'Doc deleted successfully'}
