import os
from http import HTTPStatus
from uuid import UUID

import httpx
from fastapi import Depends
from faststream.rabbit import RabbitRouter
from redis import Redis

from iaEditais.core.cache import get_redis
from iaEditais.core.dependencies import Model, Session, VStore
from iaEditais.core.settings import Settings
from iaEditais.models import DocumentRelease, Source
from iaEditais.schemas.common import WSMessage
from iaEditais.schemas.document_release import DocumentReleasePublic
from iaEditais.services import (
    notification_service,
    releases_service,
    vstore_service,
)
from iaEditais.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()
UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'
router = RabbitRouter()


@router.subscriber('notifications_send_message')
async def notifications_send_message(payload: dict, session: Session):
    user_ids = payload.get('user_ids', [])
    message_text = payload.get('message_text')

    if not user_ids or not message_text:
        return {'error': 'Invalid payload'}

    users_to_notify = await notification_service.get_users_to_notify(
        session, user_ids
    )

    if not users_to_notify:
        return {'status': 'No users found'}

    URL = SETTINGS.EVOLUTION_URL
    HEADERS = {
        'Content-Type': 'application/json',
        'apikey': SETTINGS.EVOLUTION_KEY,
    }

    results = []

    async with httpx.AsyncClient() as client:
        for user in users_to_notify:
            phone_number = notification_service.prepare_phone_number(user)

            if not phone_number:
                results.append({
                    'status': 'skipped',
                    'user_id': str(user.id),
                    'reason': 'Invalid or missing phone number',
                })
                continue

            payload = {'number': phone_number, 'text': message_text}
            try:
                response = await client.post(
                    URL, headers=HEADERS, json=payload
                )

                results.append({
                    'status': 'success'
                    if response.status_code == HTTPStatus.OK
                    else 'failed',
                    'user_id': str(user.id),
                    'status_code': response.status_code,
                    'response': response.text,
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'user_id': str(user.id),
                    'error': str(e),
                })
    return {'status': 'completed', 'results': results}


@router.subscriber('sources_create_vectors')
async def create_source_vectors(
    source_id: UUID, session: Session, vectorstore: VStore
):
    db_source = await session.get(Source, source_id)
    if not db_source:
        return {'error': 'Source not found'}
    if not db_source.file_path:
        return {'error': 'Document file_path is empty'}
    unique_filename = db_source.file_path.split('/')[-1]
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(file_path):
        return {'error': 'Document file not found'}
    documents = await vstore_service.load_document(file_path)
    chunks = vstore_service.split_documents(documents)
    presidio_anonymizer = PresidioAnonymizer()
    anonymized_chunks = presidio_anonymizer.anonymize_chunks(
        chunks, verbose=False
    )
    await vectorstore.aadd_documents(anonymized_chunks)
    return {'source_id': source_id, 'file_path': file_path}


@router.subscriber('releases_create_vectors')
@router.publisher('releases_create_check_tree')
async def create_vectors(
    release_id: UUID,
    session: Session,
    vectorstore: VStore,
    redis: Redis = Depends(get_redis),
):
    db_release = await session.get(DocumentRelease, release_id)
    if not db_release:
        return {'error': 'DocumentRelease not found'}
    if not db_release.file_path:
        return {'error': 'Document file_path is empty'}
    unique_filename = db_release.file_path.split('/')[-1]
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(file_path):
        return {'error': 'Document file not found'}

    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update', message='creating_vectors', payload=payload
    )
    await redis.publish('ws:broadcast', ws_message.model_dump_json())

    documents = await vstore_service.load_document(file_path)
    chunks = vstore_service.split_documents(documents)
    presidio_anonymizer = PresidioAnonymizer()
    anonymized_chunks = presidio_anonymizer.anonymize_chunks(
        chunks, verbose=False
    )
    await vectorstore.aadd_documents(anonymized_chunks)
    return {'release_id': release_id}


@router.subscriber('releases_create_check_tree')
@router.publisher('notifications_send_message')
async def create_check_tree(
    release_id: UUID,
    session: Session,
    vectorstore: VStore,
    model: Model,
    redis: Redis = Depends(get_redis),
):
    db_release = await session.get(DocumentRelease, release_id)
    if not db_release:
        return {'error': 'DocumentRelease not found'}
    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update', message='evaluating', payload=payload
    )
    await redis.publish('ws:broadcast', ws_message.model_dump_json())
    check_tree = await releases_service.get_check_tree(session, db_release)
    chain = releases_service.get_chain(model)
    input_vars = await releases_service.get_vars(
        check_tree, vectorstore, db_release
    )
    evaluation = await releases_service.apply_check_tree(chain, input_vars)
    applied_branch = await releases_service.save_evaluation(
        session, db_release, check_tree, evaluation, input_vars
    )
    await releases_service.create_description(
        db_release, applied_branch, model, session
    )
    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update', message='complete', payload=payload
    )
    await redis.publish('ws:broadcast', ws_message.model_dump_json())
    message_text = notification_service.format_release_message(db_release)
    db_doc = db_release.history.document
    user_ids = [editor.id for editor in db_doc.editors if editor.id]
    return {'user_ids': user_ids, 'message_text': message_text}
