from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.models import typification_model
from iaEditais.services import typification_service

router = APIRouter()


@router.post(
    '/typification/',
    status_code=HTTPStatus.CREATED,
    response_model=typification_model.Typification,
)
async def type_post(
    typification: typification_model.CreateTypification,
    conn: Connection = Depends(get_conn),
):
    return await typification_service.type_post(conn, typification)


@router.get(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=list[typification_model.Typification],
)
async def type_get_list(conn: Connection = Depends(get_conn)):
    return await typification_service.type_get(conn)


@router.get(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.OK,
    response_model=typification_model.Typification,
)
async def type_get(typification_id: UUID, conn: Connection = Depends(get_conn)):
    return await typification_service.type_get(conn, typification_id)


@router.put(
    '/typification/',
    status_code=HTTPStatus.OK,
    response_model=typification_model.Typification,
)
async def type_put(
    typification: typification_model.Typification,
    conn: Connection = Depends(get_conn),
):
    return await typification_service.type_put(conn, typification)


@router.delete(
    '/typification/{typification_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
async def type_delete(
    typification_id: UUID, conn: Connection = Depends(get_conn)
):
    return await typification_service.type_delete(conn, typification_id)
