from uuid import UUID

from faststream.rabbit import RabbitRouter

from iaEditais.core.cache import publish_update
from iaEditais.core.dependencies import Cache, Model, Session, VStore
from iaEditais.models import DocumentRelease
from iaEditais.services import releases_service, vstore_service

router = RabbitRouter()


@router.subscriber('releases_create_vectors')
@router.publisher('releases_create_check_tree')
async def create_vectors(
    release_id: UUID, session: Session, vectorstore: VStore, cache: Cache
):
    db_release = await session.get(DocumentRelease, release_id)
    file_id = db_release.file_path.split('/')[-1]
    file_path = f'iaEditais/storage/uploads/{file_id}'
    docs = await vstore_service.load_document(file_path)
    await vectorstore.aadd_documents(docs)
    await publish_update(cache, 'PROCESS_RELEASE', 'Vectors were created', {})
    return {'release_id': release_id}


@router.subscriber('releases_create_check_tree')
@router.publisher('releases_update_check_tree')
async def create_check_tree(
    release_id: UUID,
    session: Session,
    vectorstore: VStore,
    model: Model,
    cache: Cache,
):
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Iniciando verificação do lançamento...'
    )
    db_release = await session.get(DocumentRelease, release_id)
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Lançamento de documento encontrado.'
    )
    check_tree = await releases_service.get_check_tree(session, db_release)
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Árvore de verificação obtida.'
    )
    chain = releases_service.get_chain(model)
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Processo de avaliação configurado.'
    )
    input_vars = await releases_service.get_vars(
        check_tree, session, vectorstore, db_release
    )
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Variáveis de entrada preparadas.'
    )
    evaluation = await releases_service.apply_check_tree(
        chain, db_release, input_vars
    )
    await publish_update(
        cache,
        'PROCESS_RELEASE',
        'Avaliação da árvore de verificação concluída.',
    )
    applied_branch = await releases_service.save_evaluation(
        session, db_release, check_tree, evaluation
    )
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Resultado da avaliação salvo com sucesso.'
    )
    await releases_service.create_description(
        db_release, applied_branch, model, session
    )
    await publish_update(cache, 'PROCESS_RELEASE', 'Descrição final gerada.')
    await publish_update(
        cache, 'PROCESS_RELEASE', 'Processo finalizado com sucesso!', {}
    )
