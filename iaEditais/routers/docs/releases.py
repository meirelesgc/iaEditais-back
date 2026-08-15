from http import HTTPStatus
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from redis import Redis
from sqlalchemy import select

from iaEditais.core.cache import get_redis
from iaEditais.core.dependencies import (
    CurrentUser,
    Model,
    Session,
    Storage,
    VStore,
)
from iaEditais.core.settings import Settings
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentRelease,
)
from iaEditais.repositories import project_document_repo
from iaEditais.schemas import (
    DocumentReleaseList,
    DocumentReleasePublic,
)
from iaEditais.schemas.document import DocumentProcessingStatus
from iaEditais.services import audit_service, release_service, report_service
from iaEditais.workers.docs.releases import release_pipeline

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
    background_tasks: BackgroundTasks,
    model: Model,
    vstore: VStore,
    redis: Redis = Depends(get_redis),
    file: UploadFile = File(...),
    bump: str = Form('patch'),
):
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    db_doc = result.scalar_one_or_none()
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    if not db_doc.history:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='The document sent has integrity issues.',
        )
    latest_history = db_doc.history[0]
    unique_filename = f'{uuid4()}_{file.filename}'
    file_path = await storage.save(file, unique_filename)

    version = await release_service.get_next_version(
        session, doc_id, bump if bump in ('major', 'minor', 'patch') else 'patch'
    )

    db_release = DocumentRelease(
        history_id=latest_history.id,
        file_path=file_path,
        version=version,
        created_by=current_user.id,
    )

    session.add(db_release)
    db_doc.processing_status = DocumentProcessingStatus.QUEUED

    if db_doc.project_document_id:
        project_doc = await project_document_repo.get_by_id(
            session, db_doc.project_document_id
        )
        if project_doc and not project_doc.deleted_at:
            project_doc.file_path = file_path

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

    background_tasks.add_task(
        release_pipeline,
        release_id=db_release.id,
        session=session,
        model=model,
        vstore=vstore,
        redis=redis,
    )

    return db_release


class ReleaseFromFileCreate(BaseModel):
    project_document_id: UUID
    bump: str = 'patch'


@router.post(
    '/from-file',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentReleasePublic,
)
async def create_release_from_file(
    doc_id: UUID,
    payload: ReleaseFromFileCreate,
    session: Session,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    model: Model,
    vstore: VStore,
    redis: Redis = Depends(get_redis),
):
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    db_doc = result.scalar_one_or_none()
    if not db_doc or db_doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    if not db_doc.history:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='The document sent has integrity issues.',
        )

    project_doc = await project_document_repo.get_by_id(
        session, payload.project_document_id
    )
    if not project_doc or project_doc.deleted_at or not project_doc.file_path:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='File not found for this project document',
        )

    latest_history = db_doc.history[0]

    version = await release_service.get_next_version(
        session,
        doc_id,
        payload.bump
        if payload.bump in ('major', 'minor', 'patch')
        else 'patch',
    )

    db_release = DocumentRelease(
        history_id=latest_history.id,
        file_path=project_doc.file_path,
        version=version,
        created_by=current_user.id,
    )

    session.add(db_release)
    db_doc.processing_status = DocumentProcessingStatus.QUEUED

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

    background_tasks.add_task(
        release_pipeline,
        release_id=db_release.id,
        session=session,
        model=model,
        vstore=vstore,
        redis=redis,
    )

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


@router.get('/{document_release_id}/export/pdf', include_in_schema=False)
async def exportar_document_release_pdf(
    session: Session,
    document_release_id: UUID,
):
    report_path = await report_service.generate_document_release_pdf(
        session=session,
        document_release_id=document_release_id,
    )

    return FileResponse(report_path, filename=report_path.split('/')[-1])
