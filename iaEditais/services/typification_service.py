from datetime import datetime
from uuid import UUID

from iaEditais.repositories import taxonomy_repository
from iaEditais.schemas.typification import CreateTypification, Typification


async def post_typification(
    conn, typification: CreateTypification
) -> Typification:
    typification = Typification(**typification.model_dump())
    await taxonomy_repository.post_typification(conn, typification)
    return typification


async def get_typification(
    conn,
    typification_id: UUID = None,
) -> list[Typification] | Typification:
    return await taxonomy_repository.get_typification(conn, typification_id)


async def get_detailed_typification(
    conn, type_id
) -> list[Typification] | Typification:
    return await taxonomy_repository.get_typification(conn, type_id)


async def put_typification(conn, typification: Typification):
    typification.updated_at = datetime.now()
    await taxonomy_repository.put_typification(conn, typification)
    return typification


async def delete_typification(conn, typification_id: UUID):
    await taxonomy_repository.delete_typification(conn, typification_id)
    return {'message': 'Typificação deletada com sucesso.'}
