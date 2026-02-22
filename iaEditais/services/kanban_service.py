from enum import Enum
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from faststream.rabbit.fastapi import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Document, DocumentHistory, User
from iaEditais.repositories import kanban_repo
from iaEditais.schemas import DocumentPublic, DocumentStatus
from iaEditais.services import audit_service

# --- Definições de Regras de Negócio ---


class NotifyTarget(str, Enum):
    EDITORS = 'editors'
    CREATOR = 'creator'
    UNIT_AUDITORS = 'unit_auditors'


NOTIFICATION_RULES: dict[
    DocumentStatus, dict[str, bool | NotifyTarget | list[NotifyTarget]]
] = {
    DocumentStatus.PENDING: {
        'enabled': False,
        'targets': [],
    },
    DocumentStatus.UNDER_CONSTRUCTION: {
        'enabled': True,
        'targets': [NotifyTarget.EDITORS],
    },
    DocumentStatus.WAITING_FOR_REVIEW: {
        'enabled': True,
        'targets': [NotifyTarget.CREATOR, NotifyTarget.UNIT_AUDITORS],
    },
    DocumentStatus.COMPLETED: {
        'enabled': True,
        'targets': [NotifyTarget.EDITORS],
    },
}

STATUS_TRANSLATION = {
    DocumentStatus.PENDING: 'Pendente',
    DocumentStatus.UNDER_CONSTRUCTION: 'Em construção',
    DocumentStatus.WAITING_FOR_REVIEW: 'Aguardando revisão',
    DocumentStatus.COMPLETED: 'Concluído',
}

# --- Lógica Interna ---


async def _resolve_notification_targets(
    session: AsyncSession, doc: Document, status: DocumentStatus
) -> list[UUID]:
    rules = NOTIFICATION_RULES.get(status, {'enabled': False})
    if not rules['enabled']:
        return []

    targets: list[User] = []
    creator_cache = None

    for target_type in rules['targets']:
        if target_type == NotifyTarget.EDITORS:
            # Assume que doc.editors já foi carregado via selectinload no repo
            targets.extend(doc.editors)

        elif target_type == NotifyTarget.CREATOR and doc.created_by:
            if not creator_cache:
                creator_cache = await kanban_repo.get_user(
                    session, doc.created_by
                )
            if creator_cache:
                targets.append(creator_cache)

        elif target_type == NotifyTarget.UNIT_AUDITORS and doc.created_by:
            if not creator_cache:
                creator_cache = await kanban_repo.get_user(
                    session, doc.created_by
                )

            if creator_cache and creator_cache.unit_id:
                auditors = await kanban_repo.get_unit_auditors(
                    session, creator_cache.unit_id
                )
                targets.extend(auditors)

    # Remove duplicados e extrai IDs
    unique_ids = {user.id for user in targets if user.id}
    return list(unique_ids)


async def _publish_notification(
    broker: RabbitBroker,
    user_ids: list[UUID],
    doc_name: str,
    status: DocumentStatus,
):
    if not user_ids:
        return

    status_traduzido = STATUS_TRANSLATION.get(status, status.value)
    message_text = (
        f"Olá! O status do documento '{doc_name}' "
        f'foi atualizado para: {status_traduzido}'
    )

    payload = {'user_ids': user_ids, 'message_text': message_text}
    await broker.publish(payload, 'send_message')


# --- Função Principal ---


async def update_document_status(
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    new_status: DocumentStatus,
    broker: RabbitBroker,
) -> Document:
    # 1. Busca documento com relacionamentos necessários
    doc = await kanban_repo.get_with_editors(session, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Document not found'
        )

    # 2. Prepara Auditoria (Dados Antigos)
    old_data = DocumentPublic.model_validate(doc).model_dump(mode='json')

    # 3. Calcula alvos da notificação (Antes de commitar, pois precisamos dos dados atuais)
    target_user_ids = await _resolve_notification_targets(
        session, doc, new_status
    )

    # 4. Atualiza Histórico
    history = DocumentHistory(
        document_id=doc.id,
        status=new_status.value,
    )
    history.set_creation_audit(user_id)
    kanban_repo.add_history(session, history)

    # 5. Auditoria e Commit
    new_data = DocumentPublic.model_validate(doc).model_dump(mode='json')
    doc.set_update_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Document.__tablename__,
        record_id=doc.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(doc)

    # 6. Envia Notificação (Side Effect - Apenas após sucesso do commit)
    await _publish_notification(broker, target_user_ids, doc.name, new_status)

    return doc
