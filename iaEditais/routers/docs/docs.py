from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    DocumentCreate,
    DocumentFilter,
    DocumentList,
    DocumentPublic,
    DocumentUpdate,
)
from iaEditais.services import doc_service

router = APIRouter(prefix='/doc', tags=['verificação dos documentos, editais'])


@router.post('', status_code=HTTPStatus.CREATED, response_model=DocumentPublic)
async def create_doc(
    doc: DocumentCreate, session: Session, current_user: CurrentUser
):
    return await doc_service.create_doc(session, current_user, doc)


@router.get('', response_model=DocumentList)
async def read_docs(
    session: Session, filters: Annotated[DocumentFilter, Depends()]
):
    docs = await doc_service.get_docs(session, filters)
    return {'documents': docs}


@router.get('/{doc_id}', response_model=DocumentPublic)
async def read_doc(doc_id: UUID, session: Session):
    return await doc_service.get_doc_by_id(session, doc_id)


@router.put('', response_model=DocumentPublic)
async def update_doc(
    doc: DocumentUpdate, session: Session, current_user: CurrentUser
):
    return await doc_service.update_doc(session, current_user, doc)


@router.put('/{document_id}/toggle-archive', response_model=DocumentPublic)
async def toggle_archive(
    document_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    return await doc_service.toggle_archive(session, current_user, document_id)


@router.delete(
    '/{doc_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_doc(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    await doc_service.delete_doc(session, current_user, doc_id)
    return {'message': 'Doc deleted successfully'}
