import os
from uuid import UUID

from faststream.rabbit import RabbitRouter

from iaEditais.core.dependencies import Model, Session, VStore
from iaEditais.models import DocumentRelease, Source
from iaEditais.services import releases_service, vstore_service

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'

router = RabbitRouter()


@router.subscriber('sources_create_vectors')
async def create_source_vectors(
    source_id: UUID, session: Session, vectorstore: VStore
):
    db_source = await session.get(Source, source_id)
    if not db_source:
        return {'error': 'Source not found'}

    unique_filename = db_source.file_path.split('/')[-1]
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

    if not file_path:
        return {'error': 'Document for source not found'}

    documents = await vstore_service.load_document(file_path)
    chunks = vstore_service.split_documents(documents)
    await vectorstore.aadd_documents(chunks)

    return {'source_id': source_id, 'file_path': file_path}


@router.subscriber('releases_create_vectors')
@router.publisher('releases_create_check_tree')
async def create_vectors(
    release_id: UUID, session: Session, vectorstore: VStore
):
    db_release = await session.get(DocumentRelease, release_id)
    unique_filename = db_release.file_path.split('/')[-1]
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)
    documents = await vstore_service.load_document(file_path)
    chunks = vstore_service.split_documents(documents)
    await vectorstore.aadd_documents(chunks)
    return {'release_id': release_id}


@router.subscriber('releases_create_check_tree')
async def create_check_tree(
    release_id: UUID,
    session: Session,
    vectorstore: VStore,
    model: Model,
):
    db_release = await session.get(DocumentRelease, release_id)
    check_tree = await releases_service.get_check_tree(session, db_release)
    chain = releases_service.get_chain(model)
    input_vars = await releases_service.get_vars(
        check_tree, vectorstore, db_release
    )
    evaluation = await releases_service.apply_check_tree(
        chain, db_release, input_vars
    )
    applied_branch = await releases_service.save_evaluation(
        session, db_release, check_tree, evaluation
    )
    await releases_service.create_description(
        db_release, applied_branch, model, session
    )
