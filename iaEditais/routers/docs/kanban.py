from uuid import UUID

from fastapi import APIRouter

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import DocumentPublic, DocumentStatus
from iaEditais.services import kanban_service

router = APIRouter(
    prefix='/doc/{doc_id}/status',
    tags=['verificação dos documentos, kanban'],
)


@router.put('/pending', response_model=DocumentPublic)
async def set_status_pending(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await kanban_service.update_document_status(
        session, current_user.id, doc_id, DocumentStatus.PENDING
    )


@router.put('/under-construction', response_model=DocumentPublic)
async def set_status_under_construction(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await kanban_service.update_document_status(
        session, current_user.id, doc_id, DocumentStatus.UNDER_CONSTRUCTION
    )


@router.put('/waiting-review', response_model=DocumentPublic)
async def set_status_waiting_review(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await kanban_service.update_document_status(
        session, current_user.id, doc_id, DocumentStatus.WAITING_FOR_REVIEW
    )


@router.put('/completed', response_model=DocumentPublic)
async def set_status_completed(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await kanban_service.update_document_status(
        session, current_user.id, doc_id, DocumentStatus.COMPLETED
    )
