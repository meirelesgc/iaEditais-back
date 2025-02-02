from iaEditais.schemas.Guideline import Guideline
from uuid import UUID
from iaEditais.schemas.Evaluation import Evaluation
from iaEditais.repositories import conn


def post_guideline(guideline: Guideline) -> None:
    params = guideline.model_dump()
    SCRIPT_SQL = """
        INSERT INTO guidelines (id, title, description, source)
        VALUES (%(id)s, %(title)s, %(description)s, %(source)s);
        """
    conn.exec(SCRIPT_SQL, params)


def get_guidelines() -> list[Guideline]:
    params = {}
    filter_id = str()

    SCRIPT_SQL = f"""
        SELECT id, title, description, source, created_at, updated_at 
        FROM guidelines
        WHERE 1 = 1
            {filter_id};
        """
    result = conn.select(SCRIPT_SQL, params)
    return result


def post_evaluation(evaluation: Evaluation) -> None:
    params = evaluation.model_dump()
    print(params)
    SCRIPT_SQL = """
        INSERT INTO evaluations (id, guideline_id, title, description, created_at)
        VALUES (%(id)s, %(guideline_id)s, %(title)s, %(description)s, %(created_at)s);
        """
    conn.exec(SCRIPT_SQL, params)


def put_guideline(guideline: Guideline) -> str:
    params = guideline.model_dump()

    SCRIPT_SQL = """ 
        UPDATE guidelines SET 
            title = %(title)s, 
            description = %(description)s,
            source = %(source)s, 
            updated_at = NOW()
        WHERE id = %(id)s;
        """
    conn.exec(SCRIPT_SQL, params)


def delete_guideline(guideline_id: UUID) -> None:
    params = {'id': guideline_id}
    SCRIPT_SQL = """ 
        DELETE FROM guidelines WHERE id = %(id)s;
        """
    conn.exec(SCRIPT_SQL, params)


def get_evaluations() -> list[Evaluation]:
    params = {}
    filter_id = str()

    SCRIPT_SQL = f"""
        SELECT id, guideline_id, title, description, created_at, updated_at
        FROM evaluations e
        WHERE 1 = 1
            {filter_id}
        """
    result = conn.select(SCRIPT_SQL, params)
    return result


def put_evaluation(evaluation: Evaluation) -> Evaluation:
    params = evaluation.model_dump()
    SCRIPT_SQL = """
        UPDATE evaluations
        SET guideline_id = %(guideline_id)s,
            title = %(title)s,
            description = %(description)s,
            updated_at = NOW()
        WHERE id = %(id)s;
        """
    conn.exec(SCRIPT_SQL, params)
    return evaluation


def delete_evaluation(evaluation_id: UUID) -> None:
    params = {'id': evaluation_id}
    SCRIPT_SQL = """
        DELETE FROM evaluations
        WHERE id = %(id)s;
        """
    conn.exec(SCRIPT_SQL, params)
