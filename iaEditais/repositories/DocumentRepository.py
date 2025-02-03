from iaEditais.schemas.Document import Document
from uuid import UUID
from iaEditais.repositories import conn


def post_document(document: Document) -> None:
    params = document.model_dump()
    SCRIPT_SQL = """
        INSERT INTO documents (id, name, created_at, updated_at) 
        VALUES (%(id)s, %(name)s, %(created_at)s, %(updated_at)s);
        """
    conn.exec(SCRIPT_SQL, params)


def get_document(doc_id: UUID = None) -> list[Document]:
    one = False
    params = {}

    filter_id = str()
    if doc_id:
        one = True
        params['id'] = doc_id
        filter_id = 'id = %(id)s'

    SCRIPT_SQL = f"""
        SELECT id, name, created_at, updated_at
        FROM documents
        WHERE 1 = 1
            {filter_id};
        """
    results = conn.select(SCRIPT_SQL, params, one)
    return results


def get_audit(doc_id: UUID):
    params = {'id': doc_id}
    SCRIPT_SQL = """
        """
    results = conn.select(SCRIPT_SQL, params)
    return results


def delete_document(doc_id: UUID):
    params = {'id': doc_id}
    SCRIPT_SQL = """
        DELETE FROM documents 
        WHERE id = %(id)s;
        """
    conn.exec(SCRIPT_SQL, params)
