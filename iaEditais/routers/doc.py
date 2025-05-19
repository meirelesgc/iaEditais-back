from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.schemas.doc import CreateDoc, Doc, Release
from iaEditais.services import doc_service

router = APIRouter()


@router.post('/doc/', status_code=HTTPStatus.CREATED)
async def post_doc(
    doc: CreateDoc,
    conn: Connection = Depends(get_conn),
):
    return await doc_service.post_doc(conn, doc)


@router.get('/doc/', status_code=HTTPStatus.OK, response_model=list[Doc])
async def get_docs(conn: Connection = Depends(get_conn)):
    return await doc_service.get_docs(conn)


@router.delete('/doc/{doc_id}/', status_code=HTTPStatus.NO_CONTENT)
async def delete_doc(doc_id: UUID, conn: Connection = Depends(get_conn)):
    return await doc_service.delete_doc(conn, doc_id)


@router.get(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.OK,
    response_model=list[Release],
)
async def get_releases(doc_id: UUID, conn: Connection = Depends(get_conn)):
    return await doc_service.get_releases(conn, doc_id)


@router.post(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.CREATED,
    response_model=Release,
)
async def post_release(
    doc_id: UUID,
    file: UploadFile = File(...),
    conn: Connection = Depends(get_conn),
):
    return await doc_service.post_release(conn, doc_id, file)


@router.delete(
    '/doc/release/{release_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_release(
    release_id: UUID,
    conn: Connection = Depends(get_conn),
):
    return await doc_service.delete_release(conn, release_id)


@router.get(
    '/doc/release/{release_id}/',
    response_class=FileResponse,
    status_code=HTTPStatus.OK,
)
def get_release_file(release_id: UUID = None):
    return doc_service.get_release_file(release_id)
