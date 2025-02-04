from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.Evaluation import CreateEvaluation, Evaluation
from iaEditais.services import TaxonomyService
from http import HTTPStatus

router = APIRouter()


@router.post(
    '/taxonomy/evaluate/',
    response_model=Evaluation,
    status_code=HTTPStatus.CREATED,
)
def post_evaluation(evaluation: CreateEvaluation):
    return TaxonomyService.post_evaluation(evaluation)


@router.get('/taxonomy/evaluate/', response_model=list[Evaluation])
def get_evaluation():
    return TaxonomyService.get_evaluations()


@router.get(
    '/taxonomy/evaluate/{guideline_id}/',
    response_model=list[Evaluation],
)
def get_evaluation_by_guideline(guideline_id: UUID):
    return TaxonomyService.get_evaluations(guideline_id)


@router.put('/taxonomy/evaluate/', response_model=Evaluation)
def put_evaluation(evaluation: Evaluation):
    return TaxonomyService.put_evaluation(evaluation)


@router.delete(
    '/taxonomy/evaluate/{evaluation_id}/',
    status_code=HTTPStatus.NO_CONTENT,
)
def delete_evaluation(evaluation_id: UUID):
    return TaxonomyService.delete_evaluation(evaluation_id)
