from iaEditais.schemas.Document import CreateDocument, Document
from fastapi import UploadFile, HTTPException
from iaEditais.repositories import DocumentRepository
from uuid import UUID


def post_document(document: CreateDocument):
    document = Document(**document.model_dump())
    DocumentRepository.post_document(document)
    return document


def get_documents():
    return DocumentRepository.get_document()


def get_detailed_document(doc_id: UUID):
    document = DocumentRepository.get_document(doc_id)
    document['audits'] = DocumentRepository.get_audit(doc_id)
    return document


def delete_document(doc_id: UUID):
    DocumentRepository.delete_document(doc_id)
    return {'message': 'Document deleted successfully'}


def post_audit_document(doc_id: UUID, file: UploadFile):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )
