from uuid import UUID

from fastapi import Depends
from faststream.exceptions import AckMessage
from faststream.rabbit import RabbitRouter
from redis import Redis

from iaEditais.core.cache import get_redis
from iaEditais.core.dependencies import Model, Session, VStore
from iaEditais.core.settings import Settings
from iaEditais.repositories import release_repo
from iaEditais.schemas import DocumentProcessingStatus
from iaEditais.services import (
    notification_service,
    release_orchestrator,
)

SETTINGS = Settings()
router = RabbitRouter()


@router.subscriber('release_pipeline')
@router.publisher('send_message')
async def release_pipeline(
    release_id: UUID,
    session: Session,
    model: Model,
    vstore: VStore,
    redis: Redis = Depends(get_redis),
):
    # Pré-checagem rápida
    db_release = await release_repo.get_release_with_details(
        session, release_id
    )
    if not db_release:
        raise AckMessage(f'DocumentRelease {release_id} not found.')

    db_doc = db_release.history.document

    # Atualiza status inicial
    db_doc.processing_status = DocumentProcessingStatus.PROCESSING
    await session.commit()

    try:
        # Delega todo o processamento complexo para o Orchestrator
        result = await release_orchestrator.process_release_pipeline(
            session, release_id, model, vstore, redis
        )

        # Finalização no Worker
        db_doc.processing_status = DocumentProcessingStatus.IDLE
        await session.commit()

        # Prepara notificação
        message_text = notification_service.format_release_message(
            result['release']
        )
        user_ids = {editor.id for editor in db_doc.editors if editor.id}

        return {'user_ids': list(user_ids), 'message_text': message_text}

    except Exception as e:
        await session.rollback()
        db_doc.processing_status = DocumentProcessingStatus.FAILED
        release_repo.add_document(session, db_doc)
        await session.commit()
        raise e
