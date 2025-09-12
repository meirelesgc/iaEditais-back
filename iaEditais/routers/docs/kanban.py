from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session
from iaEditais.models import Document, DocumentHistory, DocumentStatus, User
from iaEditais.schemas import DocumentPublic
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


async def _set_status(
    doc: Document, status: DocumentStatus, user: User, session: Session
) -> Document:
    history = DocumentHistory(
        document_id=doc.id,
        status=status.value,
        created_by=user.id,
    )
    session.add(history)
    doc.updated_by = user.id
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc, attribute_names=['history'])
    return doc


@router.put('/pending', response_model=DocumentPublic)
async def set_status_pending(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    return await _set_status(
        doc, DocumentStatus.PENDING, current_user, session
    )


@router.put('/under-construction', response_model=DocumentPublic)
async def set_status_under_construction(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    return await _set_status(
        doc, DocumentStatus.UNDER_CONSTRUCTION, current_user, session
    )


@router.put('/waiting-review', response_model=DocumentPublic)
async def set_status_waiting_review(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    return await _set_status(
        doc, DocumentStatus.WAITING_FOR_REVIEW, current_user, session
    )


@router.put('/completed', response_model=DocumentPublic)
async def set_status_completed(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    return await _set_status(
        doc, DocumentStatus.COMPLETED, current_user, session
    )
