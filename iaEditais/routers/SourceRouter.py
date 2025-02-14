from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse

from uuid import UUID
from iaEditais.schemas.Source import Source
from iaEditais.services import SourceService
from http import HTTPStatus

router = APIRouter()


@router.post(
    '/source/',
    status_code=HTTPStatus.CREATED,
    response_model=Source,
)
def post_source(file: UploadFile = File(...)):
    return SourceService.post_source(file)


@router.get(
    '/source/',
    response_model=list[Source],
    status_code=HTTPStatus.OK,
)
def get_sources():
    return SourceService.get_sources()


@router.get(
    '/source/{source_id}/',
    response_class=FileResponse,
    status_code=HTTPStatus.OK,
)
def get_source_file(source_id: UUID = None):
    return SourceService.get_source_file(source_id)


@router.delete('/source/{source_id}/', status_code=HTTPStatus.NO_CONTENT)
def delete_source(source_id: UUID):
    return SourceService.delete_source(source_id)
