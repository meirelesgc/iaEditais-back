from iaEditais.schemas.Taxonomy import Taxonomy
from uuid import UUID
from iaEditais.schemas.Branch import Branch
from iaEditais.repositories import conn

from iaEditais.schemas.Typification import Typification


def post_typification(typification: Typification):
    params = typification.model_dump()
    SCRIPT_SQL = """
        INSERT INTO typifications (id, name, source, created_at) 
        VALUES (%(id)s, %(name)s, %(source)s, %(created_at)s);
        """
    conn().exec(SCRIPT_SQL, params)


def get_typification(
    typification_id: UUID = None,
    order_id: UUID = None,
):
    one = False
    params = {}

    filter_id = str()
    if typification_id:
        one = True
        params = {'id': typification_id}
        filter_id = 'AND id = %(id)s'

    join_order = str()
    filter_order = str()
    if order_id:
        params = {'order_id': order_id}
        join_order = """
            INNER JOIN orders o 
                ON t.id = ANY(o.typification)
            """
        filter_order = 'AND o.id = %(order_id)s'

    SCRIPT_SQL = f"""
        SELECT t.id, t.name, t.source, t.created_at, t.updated_at 
        FROM typifications t
            {join_order}
        WHERE 1 = 1
            {filter_id}
            {filter_order};
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


def post_taxonomy(taxonomy: Taxonomy) -> None:
    params = taxonomy.model_dump()
    SCRIPT_SQL = """
        INSERT INTO taxonomies (typification_id, id, title, description, source)
        VALUES (%(typification_id)s, %(id)s, %(title)s, %(description)s, %(source)s);
        """
    conn().exec(SCRIPT_SQL, params)


def get_taxonomy(
    typification_id: UUID = None,
    taxonomy_id: UUID = None,
    taxonomies: list[UUID] = None,
) -> list[Taxonomy]:
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
        SELECT typification_id, id, title, description, source, created_at, updated_at 
        FROM taxonomies
        WHERE 1 = 1
            {filter_type}
            {filter_id};
        """

    result = conn().select(SCRIPT_SQL, params, one=one)
    return result


def post_branch(branch: Branch) -> None:
    params = branch.model_dump()
    SCRIPT_SQL = """
        INSERT INTO branches (id, taxonomy_id, title, description, created_at)
        VALUES (%(id)s, %(taxonomy_id)s, %(title)s, %(description)s, %(created_at)s);
        """
    conn().exec(SCRIPT_SQL, params)


def put_taxonomy(taxonomy: Taxonomy) -> str:
    params = taxonomy.model_dump()

    SCRIPT_SQL = """ 
        UPDATE taxonomies SET 
            title = %(title)s, 
            description = %(description)s,
            source = %(source)s, 
            updated_at = %(updated_at)s
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)


def delete_taxonomy(taxonomy_id: UUID) -> None:
    params = {'id': taxonomy_id}
    SCRIPT_SQL = """ 
        DELETE FROM taxonomies WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)


def get_branches(taxonomy_id: UUID = None) -> list[Branch]:
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
    result = conn().select(SCRIPT_SQL, params)
    return result


def put_branch(branch: Branch) -> Branch:
    params = branch.model_dump()
    SCRIPT_SQL = """
        UPDATE branches
        SET taxonomy_id = %(taxonomy_id)s,
            title = %(title)s,
            description = %(description)s,
            updated_at = NOW()
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)
    return branch


def delete_branch(branch_id: UUID) -> None:
    params = {'id': branch_id}
    SCRIPT_SQL = """
        DELETE FROM branches
        WHERE id = %(id)s;
        """
    conn().exec(SCRIPT_SQL, params)
