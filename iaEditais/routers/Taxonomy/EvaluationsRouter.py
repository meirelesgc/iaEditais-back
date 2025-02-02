from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.Evaluation import CreateEvaluation, Evaluation
from iaEditais.services import TaxonomyService

router = APIRouter()


@router.post('/taxonomy/evaluations/', response_model=Evaluation)
def post_evaluation(evaluation: CreateEvaluation):
    return TaxonomyService.post_evaluation(evaluation)


@router.get('/taxonomy/evaluations/', response_model=list[Evaluation])
def get_evaluation():
    return TaxonomyService.get_evaluations()


@router.put('/taxonomy/evaluations/', response_model=Evaluation)
def put_evaluation(evaluation: Evaluation):
    return TaxonomyService.put_evaluation(evaluation)


@router.delete('/taxonomy/evaluations/{evaluation_id}/')
def delete_evaluation(evaluation_id: UUID):
    return TaxonomyService.delete_evaluation(evaluation_id)
