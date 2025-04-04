from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
from iaEditais.services import doc_service
from http import HTTPStatus
from uuid import UUID
from iaEditais.schemas.doc import CreateDoc, Doc, Release


router = APIRouter()


@router.post('/doc/', status_code=HTTPStatus.CREATED)
def post_doc(doc: CreateDoc):
    return doc_service.post_doc(doc)


@router.get('/doc/', status_code=HTTPStatus.OK, response_model=list[Doc])
def get_docs():
    return doc_service.get_docs()


@router.delete('/doc/{doc_id}/', status_code=HTTPStatus.NO_CONTENT)
def delete_doc(doc_id: UUID):
    return doc_service.delete_doc(doc_id)


@router.get(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.OK,
    response_model=list[Release],
)
def get_releases(doc_id: UUID):
    return doc_service.get_releases(doc_id)


@router.post(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.CREATED,
    response_model=Release,
)
def post_release(doc_id: UUID, file: UploadFile = File(...)):
    return doc_service.post_release(doc_id, file)


@router.delete(
    '/doc/release/{release_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
def delete_release(release_id: UUID):
    return doc_service.delete_release(release_id)


@router.get(
    '/doc/release/{release_id}/',
    response_class=FileResponse,
    status_code=HTTPStatus.OK,
)
def get_release_file(release_id: UUID = None):
    return doc_service.get_release_file(release_id)
