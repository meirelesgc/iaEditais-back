from iaEditais.schemas.Taxonomy import Taxonomy
from uuid import UUID
from iaEditais.schemas.Branch import Branch
from iaEditais.repositories import conn


def post_taxonomy(taxonomy: Taxonomy) -> None:
    params = taxonomy.model_dump()
    SCRIPT_SQL = """
        INSERT INTO taxonomies (id, title, description, source)
        VALUES (%(id)s, %(title)s, %(description)s, %(source)s);
        """
    conn().exec(SCRIPT_SQL, params)


def get_taxonomy(taxonomy_id: UUID = None) -> list[Taxonomy]:
    one = False
    params = {}
    filter_id = str()

    if taxonomy_id:
        one = True
        params['taxonomy_id'] = taxonomy_id
        filter_id = 'AND id = %(taxonomy_id)s'

    SCRIPT_SQL = f"""
        SELECT id, title, description, source, created_at, updated_at 
        FROM taxonomies
        WHERE 1 = 1
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


def get_branches(taxonomy_id: UUID) -> list[Branch]:
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
