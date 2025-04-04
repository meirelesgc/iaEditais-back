from fastapi import APIRouter
from uuid import UUID
from iaEditais.services import typification_service
from http import HTTPStatus
from iaEditais.schemas.typification import CreateTypification, Typification

router = APIRouter()


@router.post(
    '/typification/',
    status_code=HTTPStatus.CREATED,
    response_model=Typification,
)
def post_type(typification: CreateTypification):
    return typification_service.post_typification(typification)


@router.get(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=list[Typification],
)
def get_type():
    return typification_service.get_typification()


@router.get(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.OK,
    response_model=Typification,
)
def get_detailed_typification(typification_id: UUID):
    return typification_service.get_typification(typification_id)


@router.put(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=Typification,
)
def put_typification(typification: Typification):
    return typification_service.put_typification(typification)


@router.delete(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
def delete_typification(typification_id: UUID):
    return typification_service.delete_typification(typification_id)
