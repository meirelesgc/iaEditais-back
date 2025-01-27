from iaEditais.schemas.Guideline import Guideline, CreateGuideline
from iaEditais.schemas.Evaluation import Evaluation, CreateEvaluation
from iaEditais.repositories import TaxonomyRepository


def post_guideline(guideline: CreateGuideline) -> Guideline:
    guideline = Guideline(**guideline.model_dump())
    TaxonomyRepository.post_guideline(guideline)
    return guideline


def get_guidelines(guideline_id) -> list[Guideline] | Guideline:
    guidelines = TaxonomyRepository.get_guidelines(guideline_id)
    return guidelines


def put_guideline(guideline: Guideline) -> Guideline:
    TaxonomyRepository.put_guideline(guideline)
    return {'message': 'Source deleted successfully'}


def delete_guideline(guideline_id) -> dict:
    TaxonomyRepository.delete_guideline(guideline_id)
    return {'message': 'Source deleted successfully'}


def post_evaluation(evaluation: CreateEvaluation) -> Evaluation:
    evaluation = Evaluation(**evaluation.model_dump())
    TaxonomyRepository.post_evaluation(evaluation)
    return evaluation
