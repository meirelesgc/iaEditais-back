from http import HTTPStatus
from uuid import UUID, uuid4

from fastapi import File, HTTPException, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.core.settings import Settings
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentRelease,
)
from iaEditais.schemas import (
    DocumentReleaseList,
    DocumentReleasePublic,
)
from iaEditais.services import audit_service

SETTINGS = Settings()
BROKER_URL = SETTINGS.BROKER_URL

router = APIRouter(
    prefix='/doc/{doc_id}/release',
    tags=['verificação dos documentos, versões'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentReleasePublic,
)
async def create_release(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
    file: UploadFile = File(...),
):
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    db_doc = result.scalar_one_or_none()
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )

    if not db_doc.history or len(db_doc.typifications) == 0:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='The document sent has integrity issues.',
        )
    latest_history = db_doc.history[0]
    unique_filename = f'{uuid4()}_{file.filename}'
    file_path = await storage.save(file, unique_filename)

    db_release = DocumentRelease(
        history_id=latest_history.id,
        file_path=file_path,
        created_by=current_user.id,
    )

    session.add(db_release)
    await session.flush()
    await session.refresh(db_release)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='CREATE',
        table_name=DocumentRelease.__tablename__,
        record_id=db_release.id,
        old_data=None,
    )

    await session.commit()
    await router.broker.publish(db_release.id, 'release_pipeline')
    return db_release


@router.get('', response_model=DocumentReleaseList)
async def read_releases(doc_id: UUID, session: Session):
    query = (
        select(DocumentRelease)
        .join(DocumentHistory)
        .where(
            DocumentHistory.document_id == doc_id,
            DocumentRelease.deleted_at.is_(None),
        )
        .order_by(DocumentRelease.created_at.desc())
    )

    result = await session.scalars(query)
    releases = result.all()
    return {'releases': releases}


@router.delete('/{release_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_release(
    doc_id: UUID,
    release_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    query = (
        select(DocumentRelease)
        .join(DocumentHistory)
        .where(
            DocumentRelease.id == release_id,
            DocumentHistory.document_id == doc_id,
            DocumentRelease.deleted_at.is_(None),
        )
    )
    db_release = await session.scalar(query)

    if not db_release:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='File not found or does not belong to this document.',
        )

    old_data = DocumentReleasePublic.model_validate(db_release).model_dump(
        mode='json'
    )

    db_release.set_deletion_audit(current_user.id)

    await audit_service.register_action(
        session=session,
        user_id=current_user.id,
        action='DELETE',
        table_name=DocumentRelease.__tablename__,
        record_id=db_release.id,
        old_data=old_data,
    )

    await session.commit()

    return {'message': 'File deleted successfully'}
