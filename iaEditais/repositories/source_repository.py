from uuid import UUID

from iaEditais.core.connection import Connection
from iaEditais.models.source_model import Source


async def source_get(conn: Connection, source_id: UUID = None, name: str = None):
    one = False
    params = {}
    filters = str()

    if source_id:
        one = True
        filters += 'AND s.id = %(id)s '
        params['id'] = source_id

    if name:
        filters += 'AND s.name ILIKE %(name)s '
        params['name'] = f'{name}%'

    SCRIPT_SQL = f"""
        SELECT s.id, s.name, s.description, s.has_file, s.created_at,
               s.updated_at
        FROM sources s
        WHERE s.deleted_at IS NULL
            {filters};
        """
    result = await conn.select(SCRIPT_SQL, params, one)
    return result


async def souce_post(conn: Connection, source: Source) -> None:
    SCRIPT_SQL = """
        INSERT INTO sources (id, name, description, has_file, created_at)
        VALUES (%(id)s, %(name)s, %(description)s, %(has_file)s, %(created_at)s);
        """
    await conn.exec(SCRIPT_SQL, source.model_dump())


async def delete_source(conn: Connection, source_id: UUID) -> None:
    params = {'id': source_id}
    SCRIPT_SQL = """
        UPDATE sources
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def put_source(conn, source):
    params = source.model_dump()
    SCRIPT_SQL = """
        UPDATE sources
        SET name = %(name)s,
            description = %(description)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s AND deleted_at IS NULL;
        """
    await conn.exec(SCRIPT_SQL, params)
