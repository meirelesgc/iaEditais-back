import json
from uuid import UUID

from psycopg.types.json import Jsonb

from iaEditais.repositories.database import conn
from iaEditais.schemas.doc import Doc, Release


def post_doc(doc: Doc) -> None:
    params = doc.model_dump()
    SCRIPT_SQL = """
        INSERT INTO docs (id, name, typification, created_at, updated_at) 
        VALUES (%(id)s, %(name)s, %(typification)s, %(created_at)s, %(updated_at)s);
        """
    conn().exec(SCRIPT_SQL, params)


def get_doc(doc_id: UUID = None) -> list[Doc]:
    one = False
    params = {}

    filter_id = str()
    if doc_id:
        one = True
        params['id'] = doc_id
        filter_id = 'AND id = %(id)s'

    SCRIPT_SQL = f"""
        SELECT id, name, typification, created_at, updated_at
        FROM docs
        WHERE 1 = 1
            {filter_id};
        """
    results = conn().select(SCRIPT_SQL, params, one)
    return results


def get_releases(
    doc_id: UUID = None, release_id: UUID = None
) -> list[Release] | Release:
    one = False
    params = {}
    filter_id = str()

    if doc_id:
        params = {'doc_id': doc_id}
        filter_id = 'AND doc_id = %(doc_id)s'

    if release_id:
        one = True
        params = {'release_id': release_id}
        filter_id = 'AND id = %(release_id)s'

    SCRIPT_SQL = f"""
        SELECT id, doc_id, taxonomy, created_at
        FROM releases
        WHERE 1 = 1
            {filter_id}
        """
    results = conn().select(SCRIPT_SQL, params, one)
    return results


def delete_doc(doc_id: UUID):
    params = {'id': doc_id}
    SCRIPT_SQL = """
        DELETE FROM docs 
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)


def post_release(release: Release):
    params = release.model_dump()

    params['taxonomy'] = json.dumps(release.taxonomy, default=str)
    params['taxonomy'] = Jsonb(json.loads(params['taxonomy']))

    SCRIPT_SQL = """
        INSERT INTO releases (id, doc_id, taxonomy, created_at)
        VALUES (%(id)s, %(doc_id)s, %(taxonomy)s, %(created_at)s);
        """

    conn().exec(SCRIPT_SQL, params)


def delete_release(release_id: UUID):
    params = {'id': release_id}
    SCRIPT_SQL = """
        DELETE FROM releases 
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)
