from datetime import datetime
from uuid import UUID

from fastapi import Depends
from faststream.exceptions import AckMessage
from faststream.rabbit import RabbitRouter
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from iaEditais.core.cache import get_redis
from iaEditais.core.dependencies import Model, Session, VStore
from iaEditais.core.settings import Settings
from iaEditais.models import Document, DocumentHistory, DocumentRelease
from iaEditais.services import (
    notification_service,
    releases_service,
    tree_service,
    vstore_service,
)

SETTINGS = Settings()
BROKER_URL = SETTINGS.BROKER_URL
UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'

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
    result = await session.execute(
        select(DocumentRelease)
        .where(DocumentRelease.id == release_id)
        .options(
            selectinload(DocumentRelease.history)
            .selectinload(DocumentHistory.document)
            .selectinload(Document.editors)
        )
    )
    db_release = result.scalar_one_or_none()
    if not db_release:
        raise AckMessage(f'DocumentRelease {release_id} not found.')
    db_doc = db_release.history.document
    await releases_service.ws_update(redis, db_release, 'creating_vectors')
    await vstore_service.create_vectors(db_release.file_path, vstore)
    await releases_service.ws_update(redis, db_release, 'evaluating')
    tree = await tree_service.get_tree_by_release(session, db_release)
    args = await releases_service.get_eval_args(vstore, tree, db_release)
    eval_args = await releases_service.simplify_eval_args(args)
    chain = releases_service.get_chain(model)
    await releases_service.apply_tree(chain, eval_args)
    await releases_service.save_eval(session, eval_args, db_release.id, None)
    await releases_service.create_desc(session, eval_args, model, db_release)
    await releases_service.ws_update(redis, db_release, 'complete')
    message_text = notification_service.format_release_message(db_release)
    user_ids = {editor.id for editor in db_doc.editors if editor.id}
    log_path = f'iaEditais/storage/temp/{datetime.now().isoformat()}.py'
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f'eval_args = {repr(eval_args)}')
    return {'user_ids': user_ids, 'message_text': message_text}
