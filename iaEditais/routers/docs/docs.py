from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Document, User
from iaEditais.schemas import (
    DocList,
    DocPublic,
    DocumentCreate,
    DocumentUpdate,
    FilterPage,
    Message,
)
from iaEditais.security import get_current_user

router = APIRouter(prefix='/doc', tags=['verificação dos documentos, editais'])

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=DocPublic)
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
                f'Doc with name "{doc.name}" or identifier '
                f'"{doc.identifier}" already exists.'
            ),
        )

    db_doc = Document(
        name=doc.name,
        description=doc.description,
        identifier=doc.identifier,
        created_by=current_user.id,
    )
    session.add(db_doc)
    await session.commit()
    await session.refresh(db_doc)
    return db_doc


@router.get('/', response_model=DocList)
async def read_docs(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    query = await session.scalars(
        select(Document)
        .where(Document.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )
    docs = query.all()
    return {'docs': docs}


@router.get('/{doc_id}')
async def read_doc(doc_id: UUID, session: Session):
    doc = await session.get(Document, doc_id)

    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    return doc


@router.put('/', response_model=DocPublic)
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
                f'Doc with name "{doc.name}" or identifier '
                f'"{doc.identifier}" already exists.'
            ),
        )

    db_doc.name = doc.name
    db_doc.description = doc.description
    db_doc.identifier = doc.identifier
    db_doc.updated_by = current_user.id

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


@router.delete('/{doc_id}', response_model=Message)
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
