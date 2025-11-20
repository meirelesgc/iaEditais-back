import os
import re
from uuid import UUID

import httpx
from faststream.rabbit import RabbitRouter
from sqlalchemy import select

from iaEditais.core.dependencies import CacheManager, Model, Session, VStore
from iaEditais.core.settings import Settings
from iaEditais.models import DocumentRelease, Source, User
from iaEditais.schemas import DocumentReleasePublic, WSMessage
from iaEditais.services import releases_service, vstore_service
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
    statement = select(User).where(User.id.in_(user_ids))
    query = await session.scalars(statement)
    users_to_notify = query.all()
    if not users_to_notify:
        return {'status': 'No users found'}
    URL = SETTINGS.EVOLUTION_URL
    HEADERS = {
        'Content-Type': 'application/json',
        'apikey': SETTINGS.EVOLUTION_KEY,
    }
    async with httpx.AsyncClient() as client:
        for user in users_to_notify:
            if not user.phone_number:
                continue
            phone_number = user.phone_number.strip()
            phone_number = phone_number.replace(' ', '').replace('-', '')
            if not re.fullmatch(r'55\d{10,11}', phone_number):
                continue
            payload = {'number': phone_number, 'text': message_text}
            await client.post(URL, headers=HEADERS, json=payload)
    return {'status': 'success'}


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
    manager: CacheManager,
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
    manager.broadcast(ws_message)
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
    manager: CacheManager,
):
    db_release = await session.get(DocumentRelease, release_id)
    if not db_release:
        return {'error': 'DocumentRelease not found'}
    release_public = DocumentReleasePublic.model_validate(db_release)
    payload = release_public.model_dump(mode='json')
    ws_message = WSMessage(
        event='doc.release.update', message='evaluating', payload=payload
    )
    manager.broadcast(ws_message)
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
    manager.broadcast(ws_message)
    db_history = db_release.history
    db_doc = db_history.document
    message_text = (
        f"Olá! O processo de verificação do documento '{db_doc.name}' "
        f'foi concluído com sucesso.'
    )
    user_ids = [editor.id for editor in db_doc.editors if editor.id]
    return {'user_ids': user_ids, 'message_text': message_text}
