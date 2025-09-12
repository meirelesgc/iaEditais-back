import os
import shutil
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.database import get_session
from iaEditais.models import Document, DocumentHistory, DocumentRelease, User
from iaEditais.schemas import (
    DocumentReleaseList,
    DocumentReleasePublic,
    Message,
)
from iaEditais.security import get_current_user

router = APIRouter(
    prefix='/doc/{doc_id}/release',
    tags=['document releases'],
)

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentReleasePublic,
)
async def create_release(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    query = (
        select(Document)
        .options(selectinload(Document.history))
        .where(Document.id == doc_id, Document.deleted_at.is_(None))
    )

    db_doc = await session.scalar(query)

    if not db_doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    if not db_doc.history:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Document does not have a history to attach the file.',
        )
    latest_history = db_doc.history[0]

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

    try:
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    db_release = DocumentRelease(
        history_id=latest_history.id,
        file_path=file_path,
        created_by=current_user.id,
    )

    session.add(db_release)
    await session.commit()
    await session.refresh(db_release)

    return db_release


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


@router.delete(
    '/{release_id}',
    response_model=Message,
)
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
