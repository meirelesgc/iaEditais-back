from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStore

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.core.model import get_model
from iaEditais.core.vectorstore import get_vectorstore
from iaEditais.models.doc import CreateDoc, Doc, Release
from iaEditais.services import doc_service

router = APIRouter()


@router.post('/doc/', status_code=HTTPStatus.CREATED)
async def doc_post(
    doc: CreateDoc,
    conn: Connection = Depends(get_conn),
):
    return await doc_service.doc_post(conn, doc)


@router.get('/doc/', status_code=HTTPStatus.OK, response_model=list[Doc])
async def doc_get(conn: Connection = Depends(get_conn)):
    return await doc_service.doc_get(conn)


@router.delete('/doc/{doc_id}/', status_code=HTTPStatus.NO_CONTENT)
async def doc_delete(doc_id: UUID, conn: Connection = Depends(get_conn)):
    return await doc_service.delete_doc(conn, doc_id)


@router.post(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.CREATED,
    response_model=Release,
)
async def release_post(
    doc_id: UUID,
    file: UploadFile = File(...),
    conn: Connection = Depends(get_conn),
    vectorstore: VectorStore = Depends(get_vectorstore),
    model: BaseChatModel = Depends(get_model),
):
    return await doc_service.post_release(conn, vectorstore, model, doc_id, file)


@router.get(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.OK,
    response_model=list[Release],
)
async def release_get(doc_id: UUID, conn: Connection = Depends(get_conn)):
    return await doc_service.get_releases(conn, doc_id)


@router.websocket
async def release_ws(): ...


@router.get(
    '/doc/{doc_id}/release/{release_id}/',
    response_class=FileResponse,
    status_code=HTTPStatus.OK,
)
def get_release_file(release_id: UUID = None):
    return doc_service.get_release_file(release_id)


@router.delete(
    '/doc/{doc_id}/release/{release_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_release(
    release_id: UUID,
    conn: Connection = Depends(get_conn),
):
    return await doc_service.delete_release(conn, release_id)
