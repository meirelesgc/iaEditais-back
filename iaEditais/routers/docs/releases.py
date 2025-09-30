from datetime import datetime, timezone
from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from iaEditais.core.dependencies import CurrentUser, Model, Session, VStore
from iaEditais.models import (
    DocumentHistory,
    DocumentRelease,
)
from iaEditais.schemas import (
    DocumentReleaseList,
    DocumentReleasePublic,
)
from iaEditais.services import releases_service

router = APIRouter(
    prefix='/doc/{doc_id}/release',
    tags=['verificação dos documentos, versões'],
)

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


@router.post(
    '/', status_code=HTTPStatus.CREATED, response_model=DocumentReleasePublic
)
async def create_release(
    doc_id: UUID,
    session: Session,
    model: Model,
    vectorstore: VStore,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    db_release = await releases_service.create_release(
        doc_id, session, current_user, file
    )
    await releases_service.process_release(
        model, session, vectorstore, db_release
    )

    r = await session.get(
        DocumentRelease,
        db_release.id,
        options=[
            selectinload(DocumentRelease.history),
            selectinload(DocumentRelease.check_tree),
        ],
    )
    print(DocumentReleasePublic.model_validate(r))
    return r


@router.get(
    '/',
    response_model=DocumentReleaseList,
)
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

    db_release.deleted_at = datetime.now(timezone.utc)
    db_release.deleted_by = current_user.id
    await session.commit()

    return {'message': 'File deleted successfully'}
