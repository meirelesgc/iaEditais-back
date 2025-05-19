from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.schemas.typification import CreateTypification, Typification
from iaEditais.services import typification_service

router = APIRouter()


@router.post(
    '/typification/',
    status_code=HTTPStatus.CREATED,
    response_model=Typification,
)
async def post_type(
    typification: CreateTypification, conn: Connection = Depends(get_conn)
):
    return await typification_service.post_typification(conn, typification)


@router.get(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=list[Typification],
)
async def get_type(conn: Connection = Depends(get_conn)):
    return await typification_service.get_typification(conn)


@router.get(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.OK,
    response_model=Typification,
)
async def get_detailed_typification(
    typification_id: UUID, conn: Connection = Depends(get_conn)
):
    return await typification_service.get_typification(conn, typification_id)


@router.put(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=Typification,
)
async def put_typification(
    typification: Typification, conn: Connection = Depends(get_conn)
):
    return await typification_service.put_typification(conn, typification)


@router.delete(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_typification(
    typification_id: UUID, conn: Connection = Depends(get_conn)
):
    return await typification_service.delete_typification(conn, typification_id)
