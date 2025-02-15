from iaEditais.repositories import conn
from uuid import UUID
from iaEditais.schemas.Typification import Typification


def post_typification(typification: Typification):
    params = typification.model_dump()
    SCRIPT_SQL = """
        INSERT INTO typifications (id, name, source, created_at) 
        VALUES (%(id)s, %(name)s, %(source)s, %(created_at)s);
        """
    conn().exec(SCRIPT_SQL, params)


def get_typification(typification_id: UUID = None):
    one = False
    params = {}

    filter_id = str()
    if typification_id:
        one = True
        params = {'id': typification_id}
        filter_id = 'AND id = %(id)s'

    SCRIPT_SQL = f"""
        SELECT id, name, source, created_at, updated_at 
        FROM typifications
        WHERE 1 = 1
            {filter_id}
        """
    result = conn().select(SCRIPT_SQL, params, one)
    return result


def put_typification(typification: Typification):
    params = typification.model_dump()

    SCRIPT_SQL = """
        UPDATE typifications 
        SET name = %(name)s, 
            created_at = %(created_at)s,
            source = %(source)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)


def delete_typification(typification_id: UUID):
    params = {'id': typification_id}
    SCRIPT_SQL = """
        DELETE FROM typifications 
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)
