from datetime import datetime
from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException

from iaEditais.models import typification_model
from iaEditais.repositories import tree_repository


async def type_post(conn, typification: typification_model.CreateTypification):
    typification = typification_model.Typification(**typification.model_dump())
    await tree_repository.post_typification(conn, typification)
    await tree_repository.post_typification_sources(conn, typification)
    return typification


async def type_get(conn, typification_id: UUID = None):
    typification = await tree_repository.get_typification(conn, typification_id)
    if not typification:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Not found')
    return typification


async def type_put(conn, typification: typification_model.Typification):
    typification = typification_model.Typification(**typification.model_dump())
    typification.updated_at = datetime.now()
    await tree_repository.put_typification(conn, typification)
    await tree_repository.delete_typification_sources(conn, typification)
    await tree_repository.post_typification_sources(conn, typification)
    return typification


async def type_delete(conn, typification_id: UUID):
    await tree_repository.delete_typification(conn, typification_id)
    return {'message': 'Typificação deletada com sucesso.'}
