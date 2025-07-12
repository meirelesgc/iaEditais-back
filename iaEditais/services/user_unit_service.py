from iaEditais.models import user_units
from iaEditais.repositories import user_unit_repository


async def user_unit_post(conn, user_unit: user_units.CreateUserUnit):
    await user_unit_repository.user_unit_post(conn, user_unit)


async def user_unit_delete(conn, user_id, unit_id):
    await user_unit_repository.user_unit_delete(conn, user_id, unit_id)


async def user_unit_get_user(conn, user_id):
    return await user_unit_repository.user_unit_get_user(conn, user_id)


async def user_unit_get_unity(conn, unit_id):
    return await user_unit_repository.user_unit_get_unity(conn, unit_id)
