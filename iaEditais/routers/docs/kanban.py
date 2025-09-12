from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Document, User
from iaEditais.schemas import DocPublic
from iaEditais.security import get_current_user

router = APIRouter(
    prefix='/doc/{doc_id}/status', tags=['verificação dos documentos, kanban']
)

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_doc_or_404(doc_id: UUID, session: Session) -> Document:
    doc = await session.get(Document, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )
    return doc


@router.put('/pending', response_model=DocPublic)
async def set_status_pending(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    doc.status = 'pending'
    doc.updated_by = current_user.id
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)
    return doc


@router.put('/under-construction', response_model=DocPublic)
async def set_status_under_construction(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    doc.status = 'under-construction'
    doc.updated_by = current_user.id
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)
    return doc


@router.put('/waiting-review', response_model=DocPublic)
async def set_status_waiting_review(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    doc.status = 'waiting-review'
    doc.updated_by = current_user.id
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)
    return doc


@router.put('/completed', response_model=DocPublic)
async def set_status_completed(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    doc.status = 'completed'
    doc.updated_by = current_user.id
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)
    return doc
