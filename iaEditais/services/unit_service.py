from datetime import datetime

from iaEditais.models import unit_model
from iaEditais.repositories import unit_repository


async def unit_post(conn, unit):
    unit = unit_model.Unit(**unit.model_dump())
    await unit_repository.unit_post(conn, unit)
    return unit


async def unit_get(conn, id):
    return await unit_repository.unit_get(conn, id)


async def unit_put(conn, unit):
    unit = unit_model.Unit(**unit.model_dump())
    unit.updated_at = datetime.now()
    await unit_repository.unit_put(conn, unit)
    return unit


async def unit_delete(conn, id):
    await unit_repository.unit_delete(conn, id)
