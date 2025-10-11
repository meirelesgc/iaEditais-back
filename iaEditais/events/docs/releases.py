from uuid import UUID

from faststream.rabbit import RabbitRouter

from iaEditais.core.dependencies import Model, Session, VStore
from iaEditais.models import DocumentRelease
from iaEditais.services import releases_service, vstore_service

router = RabbitRouter()


@router.subscriber('releases_create_vectors')
@router.publisher('releases_create_check_tree')
async def create_vectors(
    release_id: UUID, session: Session, vectorstore: VStore
):
    db_release = await session.get(DocumentRelease, release_id)
    file_id = db_release.file_path.split('/')[-1]
    file_path = f'iaEditais/storage/uploads/{file_id}'
    docs = await vstore_service.load_document(file_path)
    await vectorstore.aadd_documents(docs)
    return {'release_id': release_id}


@router.subscriber('releases_create_check_tree')
@router.publisher('releases_att_check_tree')
async def create_check_tree(
    release_id: UUID, session: Session, vectorstore: VStore, model: Model
):
    db_release = await session.get(DocumentRelease, release_id)
    release = await releases_service.process_release(
        model, session, vectorstore, db_release
    )
