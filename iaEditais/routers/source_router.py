from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from iaEditais.schemas.source import Source
from iaEditais.services import source_service

router = APIRouter()


@router.post(
    '/source/',
    status_code=HTTPStatus.CREATED,
    response_model=Source,
)
def post_source(
    name: str = Form(...),
    description: str = Form(...),
    file: UploadFile = File(None),
):
    return source_service.post_source(name, description, file)


@router.put('/source/', status_code=HTTPStatus.OK, response_model=Source)
def put_source(source: Source):
    return source_service.put_source(source)


@router.put('/source/{source_id}/')
def put_source_file(source_id: UUID, file: UploadFile = File(None)):
    return source_service.put_source_file(source_id, file)


@router.get(
    '/source/',
    response_model=list[Source],
    status_code=HTTPStatus.OK,
)
def get_sources():
    return source_service.get_sources()


@router.get(
    '/source/{source_id}/',
    response_class=FileResponse,
    status_code=HTTPStatus.OK,
)
def get_source_file(source_id: UUID = None):
    return source_service.get_source_file(source_id)


@router.delete('/source/{source_id}/', status_code=HTTPStatus.NO_CONTENT)
def delete_source(source_id: UUID):
    return source_service.delete_source(source_id)
