from enum import Enum
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from faststream.rabbit.fastapi import RabbitBroker
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from iaEditais.core.dependencies import (
    CurrentUser,
    Session,
)
from iaEditais.models import Document, DocumentHistory, User
from iaEditais.schemas import DocumentPublic, DocumentStatus
from iaEditais.services import audit

router = APIRouter(
    prefix='/doc/{doc_id}/status', tags=['verificação dos documentos, kanban']
)


class NotifyTarget(str, Enum):
    EDITORS = 'editors'
    CREATOR = 'creator'


NOTIFICATION_RULES: dict[
    DocumentStatus, dict[str, bool | NotifyTarget | list[NotifyTarget]]
] = {
    DocumentStatus.UNDER_CONSTRUCTION: {
        'enabled': True,
        'targets': [NotifyTarget.EDITORS],
    },
    DocumentStatus.WAITING_FOR_REVIEW: {
        'enabled': True,
        'targets': [NotifyTarget.CREATOR],
    },
    DocumentStatus.PENDING: {
        'enabled': False,
        'targets': [],
    },
    DocumentStatus.COMPLETED: {
        'enabled': False,
        'targets': [],
    },
}


async def get_doc_or_404(doc_id: UUID, session: Session) -> Document:
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.editors))
        .where(Document.id == doc_id)
    )
    doc = result.scalar_one_or_none()

    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Doc not found'
        )
    return doc


async def _set_status(
    doc: Document,
    status: DocumentStatus,
    user: User,
    session: Session,
) -> Document:
    # 1. Snapshot dos dados antes da atualização
    old_data = DocumentPublic.model_validate(doc).model_dump(mode='json')

    # 2. Criação do histórico usando Mixin
    history = DocumentHistory(
        document_id=doc.id,
        status=status.value,
    )
    history.set_creation_audit(user.id)
    session.add(history)

    # 3. Atualização do Documento (updated_at/by) usando Mixin
    doc.set_update_audit(user.id)

    # 4. Registro de Auditoria (UPDATE)
    # A mudança de status é considerada uma atualização do Documento
    await audit.register_action(
        session=session,
        user_id=user.id,
        action='UPDATE',
        table_name=Document.__tablename__,
        record_id=doc.id,
        old_data=old_data,
    )

    await session.commit()
    await session.refresh(doc)
    return doc


async def _queue_notification_if_needed(
    doc: Document,
    status: DocumentStatus,
    session: Session,
    broker: RabbitBroker,
):
    status_para_portugues = {
        DocumentStatus.PENDING: 'Pendente',
        DocumentStatus.UNDER_CONSTRUCTION: 'Em construção',
        DocumentStatus.WAITING_FOR_REVIEW: 'Aguardando revisão',
        DocumentStatus.COMPLETED: 'Concluído',
    }
    rules = NOTIFICATION_RULES.get(status, {'enabled': False})
    if not rules['enabled']:
        return

    targets: list[User] = []
    for _, target in enumerate(rules['targets']):
        if target == NotifyTarget.EDITORS:
            targets.extend(doc.editors)
        elif target == NotifyTarget.CREATOR and doc.created_by:
            creator = await session.get(User, doc.created_by)
            if creator:
                targets.append(creator)

    unique_targets = {user.id: user for user in targets}.values()
    user_ids = [user.id for user in unique_targets if user.id]

    if not user_ids:
        return

    status_traduzido = status_para_portugues.get(status, status.value)
    message_text = (
        f"Olá! O status do documento '{doc.name}' "
        f'foi atualizado para: {status_traduzido}'
    )

    payload = {'user_ids': user_ids, 'message_text': message_text}
    await broker.publish(payload, 'notifications_send_message')


@router.put('/pending', response_model=DocumentPublic)
async def set_status_pending(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    doc = await get_doc_or_404(doc_id, session)
    await _queue_notification_if_needed(
        doc, DocumentStatus.PENDING, session, router.broker
    )
    return await _set_status(
        doc, DocumentStatus.PENDING, current_user, session
    )


@router.put('/under-construction', response_model=DocumentPublic)
async def set_status_under_construction(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    doc = await get_doc_or_404(doc_id, session)
    await _queue_notification_if_needed(
        doc, DocumentStatus.UNDER_CONSTRUCTION, session, router.broker
    )
    return await _set_status(
        doc, DocumentStatus.UNDER_CONSTRUCTION, current_user, session
    )


@router.put('/waiting-review', response_model=DocumentPublic)
async def set_status_waiting_review(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    doc = await get_doc_or_404(doc_id, session)
    await _queue_notification_if_needed(
        doc, DocumentStatus.WAITING_FOR_REVIEW, session, router.broker
    )
    return await _set_status(
        doc, DocumentStatus.WAITING_FOR_REVIEW, current_user, session
    )


@router.put('/completed', response_model=DocumentPublic)
async def set_status_completed(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    doc = await get_doc_or_404(doc_id, session)
    await _queue_notification_if_needed(
        doc, DocumentStatus.COMPLETED, session, router.broker
    )
    return await _set_status(
        doc, DocumentStatus.COMPLETED, current_user, session
    )
