from uuid import UUID

from iaEditais.core.connection import Connection
from iaEditais.schemas.source import Source


async def get_source(
    conn: Connection,
    source_id: UUID = None,
    name: str = None,
) -> list[Source] | Source:
    one = False
    params = {}

    filter_id = str()
    if source_id:
        one = True
        filter_id = 'AND s.id = %(id)s'
        params['id'] = source_id

    filter_name = str()
    if name:
        filter_name += 'AND s.name ILIKE %(name)s'
        params['name'] = f'{name}%'

    SCRIPT_SQL = f"""
        SELECT s.id, s.name, s.description, s.has_file, s.created_at,
            s.updated_at
        FROM sources s
        WHERE 1 = 1
            {filter_name}
            {filter_id};
        """
    result = await conn.select(SCRIPT_SQL, params, one)
    return result


async def post_source(conn: Connection, source: Source) -> None:
    SCRIPT_SQL = """
        INSERT INTO sources (id, name, description, has_file, created_at)
        VALUES (%(id)s, %(name)s, %(description)s, %(has_file)s, %(created_at)s);
        """
    await conn.exec(SCRIPT_SQL, source.model_dump())


async def delete_source(conn: Connection, source_id: UUID) -> None:
    params = {'id': source_id}
    SCRIPT_SQL = """
        DELETE FROM sources WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def put_source(conn, source: Source):
    params = source.model_dump()
    SCRIPT_SQL = """
        UPDATE public.sources
        SET name = %(name)s,
            description = %(description)s,
            has_file = %(has_file)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)
