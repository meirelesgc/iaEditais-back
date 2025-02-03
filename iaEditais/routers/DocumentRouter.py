from fastapi import APIRouter, File, UploadFile
from iaEditais.services import DocumentService
from http import HTTPStatus
from uuid import UUID
from iaEditais.schemas.Document import CreateDocument

router = APIRouter()


@router.post('/document/', status_code=HTTPStatus.CREATED)
def post_documene(document: CreateDocument):
    return DocumentService.post_document(document)


@router.get('/document/', status_code=HTTPStatus.OK)
def get_documents():
    return DocumentService.get_documents()


# Não implementado ainda
@router.get('/document/{doc_id}/', status_code=HTTPStatus.OK)
def get_detailed_documents(doc_id: UUID):
    return DocumentService.get_detailed_document(doc_id)


@router.delete('/document/{doc_id}', status_code=HTTPStatus.OK)
def delete_document(doc_id: UUID):
    return DocumentService.delete_document(doc_id)


@router.post('/document/{doc_id}/audit/', status_code=HTTPStatus.OK)
def post_audit_document(doc_id: UUID, file: UploadFile = File(...)):
    return DocumentService.post_audit_document(doc_id, file)
