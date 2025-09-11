from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Doc
from iaEditais.schemas import (
    DocCreate,
    DocList,
    DocPublic,
    DocUpdate,
    FilterPage,
    Message,
)

router = APIRouter(prefix='/doc', tags=['verificação de entidades, editais'])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.post('/', status_code=HTTPStatus.CREATED, response_model=DocPublic)
async def create_doc(doc: DocCreate, session: Session):
    db_doc = await session.scalar(
        select(Doc).where(
            Doc.deleted_at.is_(None),
            or_(Doc.name == doc.name, Doc.identifier == doc.identifier),
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

    db_doc = Doc(
        name=doc.name,
        description=doc.description,
        identifier=doc.identifier,
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
        select(Doc)
        .where(Doc.deleted_at.is_(None))
        .offset(filters.offset)
        .limit(filters.limit)
    )
    docs = query.all()
    return {'docs': docs}


@router.get('/{doc_id}')
async def read_doc(doc_id: UUID, session: Session):
    doc = await session.get(Doc, doc_id)

    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    return doc


@router.put('/', response_model=DocPublic)
async def update_doc(doc: DocUpdate, session: Session):
    db_doc = await session.get(Doc, doc.id)
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    db_doc_conflict = await session.scalar(
        select(Doc).where(
            Doc.deleted_at.is_(None),
            Doc.id != doc.id,
            or_(Doc.name == doc.name, Doc.identifier == doc.identifier),
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

    await session.commit()
    await session.refresh(db_doc)
    return db_doc


@router.delete('/{doc_id}', response_model=Message)
async def delete_doc(doc_id: UUID, session: Session):
    db_doc = await session.get(Doc, doc_id)

    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    db_doc.deleted_at = datetime.now(timezone.utc)
    await session.commit()

    return {'message': 'Doc deleted successfully'}
