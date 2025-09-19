from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.core.database import get_session
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentStatus,
    Typification,
    User,
)
from iaEditais.schemas import (
    DocumentCreate,
    DocumentList,
    DocumentPublic,
    DocumentUpdate,
    FilterPage,
)
from iaEditais.security import get_current_user

router = APIRouter(prefix='/doc', tags=['verificação dos documentos, editais'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    '/', status_code=HTTPStatus.CREATED, response_model=DocumentPublic
)
async def create_doc(
    doc: DocumentCreate, session: Session, current_user: CurrentUser
):
    db_doc = await session.scalar(
        select(Document).where(
            Document.deleted_at.is_(None),
            or_(
                Document.name == doc.name,
                Document.identifier == doc.identifier,
            ),
        )
    )
    if db_doc:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=(
                f'Doc with name "{doc.name}" or identifier "{doc.identifier}" already exists.'
            ),
        )

    db_doc = Document(
        name=doc.name,
        description=doc.description,
        identifier=doc.identifier,
        created_by=current_user.id,
    )
    session.add(db_doc)
    await session.flush()

    history = DocumentHistory(
        document_id=db_doc.id,
        status=DocumentStatus.PENDING.value,
        created_by=current_user.id,
    )
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

    await session.commit()
    await session.refresh(db_doc, attribute_names=['history', 'typifications'])
    return db_doc


@router.get('/', response_model=DocumentList)
async def read_docs(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Document)
        .where(Document.deleted_at.is_(None))
        .options(
            selectinload(Document.history),
            selectinload(Document.typifications),
            selectinload(Document.editors),
        )
        .offset(filters.offset)
        .limit(filters.limit)
    )
    docs = query.all()
    return {'documents': docs}


@router.get('/{doc_id}', response_model=DocumentPublic)
async def read_doc(doc_id: UUID, session: Session):
    doc = await session.get(
        Document,
        doc_id,
        options=[
            selectinload(Document.history),
            selectinload(Document.typifications),
        ],
    )
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )
    return doc


@router.put('/', response_model=DocumentPublic)
async def update_doc(
    doc: DocumentUpdate, session: Session, current_user: CurrentUser
):
    db_doc = await session.get(Document, doc.id)
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    db_doc_conflict = await session.scalar(
        select(Document).where(
            Document.deleted_at.is_(None),
            Document.id != doc.id,
            or_(
                Document.name == doc.name,
                Document.identifier == doc.identifier,
            ),
        )
    )
    if db_doc_conflict:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=(
                f'Doc with name "{doc.name}" or identifier "{doc.identifier}" already exists.'
            ),
        )

    db_doc.name = doc.name
    db_doc.description = doc.description
    db_doc.identifier = doc.identifier
    db_doc.updated_by = current_user.id

    if doc.typification_ids is not None:
        typifications = await session.scalars(
            select(Typification).where(
                Typification.id.in_(doc.typification_ids)
            )
        )
        db_doc.typifications = [typ for typ in typifications.all()]

    await session.commit()
    await session.refresh(
        db_doc,
        attribute_names=['history', 'typifications', 'updated_at'],
    )
    return db_doc


@router.delete(
    '/{doc_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_doc(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    db_doc = await session.get(Document, doc_id)

    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    db_doc.deleted_at = datetime.now(timezone.utc)
    db_doc.deleted_by = current_user.id
    await session.commit()

    return {'message': 'Doc deleted successfully'}
