from iaEditais.repositories import conn
from uuid import UUID
from iaEditais.schemas.Source import Source


def get_source(
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
        SELECT s.id, s.name, s.description, s.has_file, s.created_at, s.updated_at
        FROM sources s
        WHERE 1 = 1
            {filter_name}
            {filter_id};
        """
    result = conn().select(SCRIPT_SQL, params, one)
    return result


def post_source(source: Source) -> None:
    SCRIPT_SQL = """
        INSERT INTO sources (id, name, description, has_file, created_at)
        VALUES (%(id)s, %(name)s, %(description)s, %(has_file)s, %(created_at)s);
        """
    conn().exec(SCRIPT_SQL, source.model_dump())


def delete_source(source_id: UUID) -> None:
    params = {'id': source_id}
    SCRIPT_SQL = """
        DELETE FROM sources WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)
