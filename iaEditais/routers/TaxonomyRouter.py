from fastapi import APIRouter
from uuid import UUID
from iaEditais.schemas.Guideline import CreateGuideline, Guideline
from iaEditais.schemas.Evaluation import CreateEvaluation, Evaluation
from iaEditais.services import TaxonomyService
from typing import List

router = APIRouter()


@router.post('/taxonomy/guidelines/')
def post_guideline(guideline: CreateGuideline) -> Guideline:
    guideline = TaxonomyService.post_guideline(guideline)
    return guideline


@router.get('/taxonomy/guidelines/', response_model=List[Guideline])
@router.get('/taxonomy/guidelines/{guideline_id}/', response_model=Guideline)
def get_guideline(guideline_id: UUID = None):
    guidelines = TaxonomyService.get_guidelines(guideline_id)
    return guidelines


@router.put('/taxonomy/guidelines/')
def put_guideline(guideline: Guideline):
    return TaxonomyService.put_guideline(guideline)


@router.delete('/taxonomy/guidelines/{guideline_id}/')
def delete_guideline(guideline_id: UUID):
    return TaxonomyService.delete_guideline(guideline_id)


@router.post('/taxonomy/evaluations/')
def post_evaluation(evaluation: CreateEvaluation) -> Evaluation:
    evaluation = TaxonomyService.post_evaluation(evaluation)
    return evaluation
