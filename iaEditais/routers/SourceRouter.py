from fastapi import APIRouter, File, UploadFile

from uuid import UUID
from iaEditais.schemas.Source import Source
from iaEditais.services import SourceService
from http import HTTPStatus

router = APIRouter()


@router.post('/source/', status_code=HTTPStatus.OK)
def create_source(file: UploadFile = File(...)) -> Source:
    source = SourceService.post_source(file)
    return source


@router.get('/source/', response_model=Source | list[Source])
def get_sources():
    sources = SourceService.get_sources()
    return sources


@router.get('/source/{source_id}/', response_model=Source)
def get_source_file(source_id: UUID = None):
    return SourceService.get_source_file(source_id)


@router.delete('/source/{source_id}/')
def delete_source(source_id: UUID):
    return SourceService.delete_source(source_id)
