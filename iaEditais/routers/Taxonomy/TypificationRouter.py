from fastapi import APIRouter
from uuid import UUID
from iaEditais.services import TypificationService
from http import HTTPStatus
from iaEditais.schemas.Typification import CreateTypification, Typification

router = APIRouter()


@router.post(
    '/typification/',
    status_code=HTTPStatus.CREATED,
    response_model=Typification,
)
def post_type(typification: CreateTypification):
    return TypificationService.post_typification(typification)


@router.get(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=list[Typification],
)
def get_type():
    return TypificationService.get_typification()


@router.get(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.OK,
    response_model=Typification,
)
def get_detailed_typification(typification_id: UUID):
    return TypificationService.get_typification(typification_id)


@router.put(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=Typification,
)
def put_typification(typification: Typification):
    return TypificationService.put_typification(typification)


@router.delete(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
def delete_typification(typification_id: UUID):
    return TypificationService.delete_typification(typification_id)
