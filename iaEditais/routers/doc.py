from http import HTTPStatus
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStore
from redis.asyncio import Redis

from iaEditais.core.cache import get_cache
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


@router.put('/doc/', status_code=HTTPStatus.CREATED)
async def doc_put(
    doc: Doc,
    conn: Connection = Depends(get_conn),
):
    return await doc_service.doc_put(conn, doc)


@router.get('/doc/', status_code=HTTPStatus.OK, response_model=list[Doc])
async def doc_get(conn: Connection = Depends(get_conn)):
    return await doc_service.doc_get(conn)


@router.put('/doc/{doc_id}/status/pending', status_code=HTTPStatus.OK)
async def set_status_pending(doc_id: UUID, conn: Connection = Depends(get_conn)):
    return await doc_service.update_status(conn, doc_id, 'PENDING')


@router.put('/doc/{doc_id}/status/under-construction', status_code=HTTPStatus.OK)
async def set_status_under_construction(
    doc_id: UUID, conn: Connection = Depends(get_conn)
):
    return await doc_service.update_status(conn, doc_id, 'UNDER CONSTRUCTION')


@router.put('/doc/{doc_id}/status/waiting-review', status_code=HTTPStatus.OK)
async def set_status_waiting_review(
    doc_id: UUID, conn: Connection = Depends(get_conn)
):
    return await doc_service.update_status(conn, doc_id, 'WAITING FOR REVIEW')


@router.put('/doc/{doc_id}/status/completed', status_code=HTTPStatus.OK)
async def set_status_completed(
    doc_id: UUID, conn: Connection = Depends(get_conn)
):
    return await doc_service.update_status(conn, doc_id, 'COMPLETED')


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
    redis: Redis = Depends(get_cache),
):
    return await doc_service.post_release(
        conn, vectorstore, model, doc_id, file, redis
    )


@router.websocket('/ws/doc/{doc_id}/release/{release_id}/')
async def release_ws(
    websocket: WebSocket,
    doc_id: UUID,
    release_id: UUID,
    redis: Redis = Depends(get_cache),
):
    key = f'task:{doc_id}:{release_id}:progress'
    await websocket.accept()
    async with redis.pubsub() as pubsub:
        await pubsub.subscribe(key)
        try:
            async for message in pubsub.listen():
                if message['type'] != 'message':
                    continue
                await websocket.send_text(message['data'])
        except WebSocketDisconnect:
            pass


@router.get(
    '/doc/{doc_id}/release/',
    status_code=HTTPStatus.OK,
    response_model=list[Release],
)
async def release_get(doc_id: UUID, conn: Connection = Depends(get_conn)):
    return await doc_service.get_releases(conn, doc_id)


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
