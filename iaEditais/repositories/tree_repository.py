from uuid import UUID

from iaEditais.core.connection import Connection
from iaEditais.models.branch_model import Branch


async def post_typification(conn, typification):
    params = typification.model_dump()
    SCRIPT_SQL = """
        INSERT INTO typifications (id, name, created_at)
        VALUES (%(id)s, %(name)s, %(created_at)s);
        """
    await conn.exec(SCRIPT_SQL, params)


async def post_typification_sources(conn, typification):
    params = typification.model_dump()
    params = [{'id': params['id'], 'source_id': s} for s in params['source']]

    SCRIPT_SQL = """
        INSERT INTO typification_sources (typification_id, source_id)
        VALUES (%(id)s, %(source_id)s);
        """
    await conn.executemany(SCRIPT_SQL, params)


async def delete_typification_sources(conn, typification):
    params = {'typification_id': typification.id}
    SCRIPT_SQL = """
        DELETE FROM typification_sources
        WHERE typification_id = %(typification_id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def delete_typification(conn, typification_id: UUID):
    params = {'id': typification_id}
    SCRIPT_SQL = """
        UPDATE typifications
        SET deleted_at = NOW()
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def get_typification(
    conn: Connection,
    typification_id: UUID = None,
    doc_id: UUID = None,
):
    one = False
    params = {}

    filter_id = str()
    if typification_id:
        one = True
        params = {'id': typification_id}
        filter_id = 'AND id = %(id)s'

    join_doc = str()
    filter_doc = str()
    if doc_id:
        params = {'doc_id': doc_id}
        join_doc = """
            INNER JOIN docs o
                ON t.id = ANY(o.typification)
            """
        filter_doc = 'AND o.id = %(doc_id)s'

    SCRIPT_SQL = f"""
        SELECT t.id, t.name, ARRAY_REMOVE(ARRAY_AGG(ts.source_id), NULL)
            AS source, t.created_at, t.updated_at
        FROM typifications t
            LEFT JOIN typification_sources ts
                ON t.id = ts.typification_id
            {join_doc}
        WHERE 1 = 1
            AND t.deleted_at IS NULL
            {filter_id}
            {filter_doc}
        GROUP BY t.id;
        """
    return await conn.select(SCRIPT_SQL, params, one)


async def put_typification(conn, typification):
    params = typification.model_dump()

    SCRIPT_SQL = """
        UPDATE typifications
        SET name = %(name)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def post_taxonomy(conn, taxonomy) -> None:
    params = taxonomy.model_dump()
    SCRIPT_SQL = """
        INSERT INTO taxonomies (typification_id, id, title, description)
        VALUES (%(typification_id)s, %(id)s, %(title)s, %(description)s);
        """
    await conn.exec(SCRIPT_SQL, params)


async def post_taxonomy_sources(conn, typification):
    params = typification.model_dump()
    params = [{'id': params['id'], 'source_id': s} for s in params['source']]

    SCRIPT_SQL = """
        INSERT INTO taxonomy_sources (taxonomy_id, source_id)
        VALUES (%(id)s, %(source_id)s);
        """
    await conn.executemany(SCRIPT_SQL, params)


async def delete_taxonomy_sources(conn, typification):
    params = typification.model_dump()
    SCRIPT_SQL = """
        DELETE FROM taxonomy_sources
        WHERE taxonomy_id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def get_taxonomy(
    conn: Connection,
    typification_id: UUID = None,
    taxonomy_id: UUID = None,
    taxonomies: list[UUID] = None,
):
    one = False
    params = {}

    filter_type = str()
    if typification_id:
        params['typification_id'] = typification_id
        filter_type = 'AND typification_id = %(typification_id)s'

    filter_id = str()
    if taxonomy_id:
        one = True
        params['taxonomy_id'] = taxonomy_id
        filter_id = 'AND id = %(taxonomy_id)s'

    if taxonomies:
        one = False
        params['taxonomies'] = taxonomies
        filter_id = 'AND id = ANY(%(taxonomies)s)'

    SCRIPT_SQL = f"""
        SELECT tx.typification_id, tx.id, tx.title, tx.description,
            ARRAY_REMOVE(ARRAY_AGG(txs.source_id), NULL) AS source,
            tx.created_at, tx.updated_at
        FROM taxonomies tx
            LEFT JOIN taxonomy_sources txs
                ON tx.id = txs.taxonomy_id
        WHERE 1 = 1
            {filter_type}
            {filter_id}
        GROUP BY tx.id;
        """

    result = await conn.select(SCRIPT_SQL, params, one=one)
    return result


async def post_branch(conn, branch: Branch) -> None:
    params = branch.model_dump()
    SCRIPT_SQL = """
        INSERT INTO branches (id, taxonomy_id, title, description, created_at)
        VALUES (%(id)s, %(taxonomy_id)s, %(title)s, %(description)s,
            %(created_at)s);
        """
    await conn.exec(SCRIPT_SQL, params)


async def put_taxonomy(conn, taxonomy) -> str:
    params = taxonomy.model_dump()

    SCRIPT_SQL = """
        UPDATE taxonomies SET
            title = %(title)s,
            description = %(description)s,
            updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def delete_taxonomy(conn, taxonomy_id: UUID) -> None:
    params = {'id': taxonomy_id}
    SCRIPT_SQL = """
        UPDATE taxonomies
        SET deleted_at = NOW()
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)


async def get_branches(conn: Connection, taxonomy_id: UUID = None):
    params = {}
    filter_id = str()

    if taxonomy_id:
        params['taxonomy_id'] = taxonomy_id
        filter_id = 'AND taxonomy_id = %(taxonomy_id)s'

    SCRIPT_SQL = f"""
        SELECT id, taxonomy_id, title, description, created_at, updated_at
        FROM branches
        WHERE 1 = 1
            {filter_id}
        """
    result = await conn.select(SCRIPT_SQL, params)
    return result


async def put_branch(conn, branch: Branch) -> Branch:
    params = branch.model_dump()
    SCRIPT_SQL = """
        UPDATE branches
        SET taxonomy_id = %(taxonomy_id)s,
            title = %(title)s,
            description = %(description)s,
            updated_at = NOW()
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)
    return branch


async def delete_branch(conn, branch_id: UUID) -> None:
    params = {'id': branch_id}
    SCRIPT_SQL = """
        UPDATE branches
        SET deleted_at = NOW()
        WHERE id = %(id)s;
        """
    await conn.exec(SCRIPT_SQL, params)
