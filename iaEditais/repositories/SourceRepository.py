from iaEditais.repositories import conn
from uuid import UUID
from iaEditais.schemas.Source import Source


def get_source() -> list[Source] | Source:
    params = {}
    filter_id = str()

    SCRIPT_SQL = f"""
        SELECT s.id, s.name, s.created_at, s.updated_at
        FROM sources s
        WHERE 1 = 1
            {filter_id}
        """
    result = conn.select(SCRIPT_SQL, params)
    return result


def post_source(source: Source) -> None:
    SCRIPT_SQL = """
        INSERT INTO sources (id, name, created_at)
        VALUES (%(id)s, %(name)s, %(created_at)s);
        """
    conn.exec(SCRIPT_SQL, source.model_dump())


def delete_source(source_id: UUID) -> None:
    params = {'id': source_id}
    SCRIPT_SQL = """
        DELETE FROM sources WHERE id = %(id)s;
        """
    conn.exec(SCRIPT_SQL, params)
