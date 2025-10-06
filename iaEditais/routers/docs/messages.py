from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Document, DocumentMessage
from iaEditais.schemas import DocumentMessageCreate, DocumentMessagePublic

router = APIRouter(
    prefix='/doc', tags=['verificação dos documentos, mensagens']
)


@router.post(
    '/{doc_id}/message',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentMessagePublic,
)
async def create_document_message(
    doc_id: UUID,
    message_data: DocumentMessageCreate,
    session: Session,
    current_user: CurrentUser,
):
    db_doc = await session.get(
        Document, doc_id, options=[selectinload(Document.history)]
    )

    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Documento não encontrado.',
        )

    latest_history = db_doc.history[0] if db_doc.history else None
    if not latest_history:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail='O documento não possui um histórico para associar a mensagem.',
        )

    db_message = DocumentMessage(
        history_id=latest_history.id,
        message=message_data.message,
        user_id=current_user.id,
        created_by=current_user.id,
    )

    latest_history.messages.append(db_message)

    session.add(db_message)
    await session.commit()
    await session.refresh(db_message)

    return db_message
