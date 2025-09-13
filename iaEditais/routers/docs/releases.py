from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from langchain_core.vectorstores import VectorStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.database import get_session, get_vectorstore
from iaEditais.models import DocumentHistory, DocumentRelease, User
from iaEditais.schemas import (
    DocumentReleaseList,
    DocumentReleasePublic,
    Message,
)
from iaEditais.security import get_current_user
from iaEditais.services import releases_service

router = APIRouter(
    prefix='/doc/{doc_id}/release',
    tags=['verificação dos documentos, versões'],
)

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
VStore = Annotated[VectorStore, Depends(get_vectorstore)]

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentReleasePublic,
)
async def create_release(
    doc_id: UUID,
    session: Session,
    vectorstore: VStore,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    release = await releases_service.create_release(
        doc_id, session, vectorstore, current_user, file
    )
    return release


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
