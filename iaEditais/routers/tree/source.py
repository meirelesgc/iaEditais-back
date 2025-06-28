from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import Message, source_model
from iaEditais.services import source_service

router = APIRouter()


@router.post(
    '/source/',
    status_code=HTTPStatus.CREATED,
    response_model=source_model.Source,
)
async def source_post(
    source: source_model.CreateSource,
    conn: Connection = Depends(get_conn),
):
    return await source_service.source_post(conn, source)


@router.get(
    '/source/{source_id}/',
    response_model=source_model.Source,
    status_code=HTTPStatus.OK,
)
async def source_get(
    source_id: UUID,
    conn: Connection = Depends(get_conn),
):
    return await source_service.source_get(conn, source_id)


@router.post(
    '/source/{source_id}/upload/',
    status_code=HTTPStatus.OK,
    response_model=Message,
)
async def source_upload_post(
    source_id: UUID,
    file: UploadFile = File(...),
    conn: Connection = Depends(get_conn),
):
    return await source_service.source_upload_post(conn, source_id, file)


@router.delete(
    '/source/{source_id}/upload/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def source_upload_delete(
    source_id: UUID,
    conn: Connection = Depends(get_conn),
):
    return await source_service.source_upload_delete(conn, source_id)


@router.put(
    '/source/',
    status_code=HTTPStatus.OK,
    response_model=source_model.Source,
)
async def source_put(
    source: source_model.SourceUpdate,
    conn: Connection = Depends(get_conn),
):
    return await source_service.source_put(conn, source)


@router.get(
    '/source/',
    response_model=list[source_model.Source],
    status_code=HTTPStatus.OK,
)
async def source_get_list(conn: Connection = Depends(get_conn)):
    return await source_service.source_get(conn, None)


@router.get(
    '/source/{source_id}/upload/',
    response_class=FileResponse,
    status_code=HTTPStatus.OK,
)
def source_upload_get(
    source_id: UUID = None,
):
    return source_service.source_upload_get(source_id)


@router.delete('/source/{source_id}/', status_code=HTTPStatus.NO_CONTENT)
async def source_delete(source_id: UUID, conn: Connection = Depends(get_conn)):
    return await source_service.source_delete(conn, source_id)
