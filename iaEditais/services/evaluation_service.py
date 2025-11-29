import asyncio
import logging
from typing import Optional
from uuid import UUID

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase
from deepeval.test_case import LLMTestCaseParams
from fastapi import File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import (
    AIModel,
    AppliedTaxonomy,
    AppliedTypification,
    DocumentRelease,
    Metric,
)
from iaEditais.repositories import evaluation_repository
from iaEditais.services import releases_service

logger = logging.getLogger(__name__)


async def wait_for_release_processing(session: Session, release_id: UUID) -> DocumentRelease:
    """
    Aguarda o processamento do release ser concluído.
    Verifica se o campo 'description' foi preenchido, o que ocorre na etapa final.
    """
    max_retries = 60  # 5 minutes (60 * 5s)
    for _ in range(max_retries):
        # Refresh release with full tree
        stmt = (
            select(DocumentRelease)
            .where(DocumentRelease.id == release_id)
            .options(
                selectinload(DocumentRelease.check_tree)
                .selectinload(AppliedTypification.taxonomies)
                .selectinload(AppliedTaxonomy.branches)
            )
        )
        release = await session.scalar(stmt)
        
        if release and release.description:
            return release
        
        await asyncio.sleep(5)
    
    raise TimeoutError("Timeout waiting for release processing")


async def process_test_case(
    session: Session, 
    test_case, 
    metric_id: UUID, 
    model_id: Optional[UUID], 
    processed_release: DocumentRelease, 
    test_run_id: UUID, 
    current_user: CurrentUser
):
    """
    Executa a avaliação de um caso de teste utilizando DeepEval.
    Compara o resultado do processamento (AppliedBranch) com o esperado (TestCase).
    """

    print(f"3. Processing test case: {test_case.id}")
    # 1. Busca Métrica e Modelo
    metric_db = await session.get(Metric, metric_id)
    if not metric_db:
        raise ValueError(f"Metric {metric_id} not found")

    # 2. Encontra o AppliedBranch correspondente ao TestCase
    target_branch = None
    if test_case.branch_id:
        for typ in processed_release.check_tree:
            for tax in typ.taxonomies:
                for branch in tax.branches:
                    if branch.original_id == test_case.branch_id:
                        target_branch = branch
                        break
                if target_branch:
                    break
            if target_branch:
                break
    
    actual_output = "Nenhum resultado gerado para este item."
    if target_branch and target_branch.feedback:
        actual_output = target_branch.feedback

    # 3. Prepara LLMTestCase do DeepEval
    llm_test_case = LLMTestCase(
        input=test_case.input or test_case.name,
        actual_output=actual_output,
        expected_output=test_case.expected_feedback
    )

    # 4. Configura Métrica GEval
    # Mapeia steps do banco para lista de strings
    eval_steps = []
    if metric_db.evaluation_steps:
        eval_steps = [step.strip() for step in metric_db.evaluation_steps.split('\n') if step.strip()]

    metric = GEval(
        name=metric_db.name,
        criteria=metric_db.criteria,
        evaluation_steps=eval_steps,
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
        model='gpt-4o-mini', # Pode ser parametrizável, mas GEval usa um modelo para julgar
        threshold=metric_db.threshold or 0.5
    )

    # 5. Executa Avaliação
    try:
        metric.measure(llm_test_case)
        score = metric.score
        reason = metric.reason
        passed = metric.is_successful()
    except Exception as e:
        logger.error("Error executing DeepEval metric: %s", e)
        score = 0.0
        reason = f"Error evaluating: {str(e)}"
        passed = False

    # 6. Salva Resultado
    result_data = {
        'test_run_id': test_run_id,
        'test_case_id': test_case.id,
        'metric_id': metric_id,
        'model_id': model_id,
        'threshold_used': metric_db.threshold,
        'reason_feedback': reason,
        'score_feedback': score,
        'passed_feedback': passed,
        'actual_feedback': actual_output,
        'actual_fulfilled': target_branch.fulfilled if target_branch else False,
        'passed_fulfilled': (target_branch.fulfilled == test_case.expected_fulfilled) if target_branch else False,
        'created_by': current_user.id
    }
    
    result_id = await evaluation_repository.create_test_result(session, result_data)
    
    return {
        'test_case_id': str(test_case.id),
        'metric_id': str(metric_id),
        'result_id': str(result_id),
        'passed': passed,
        'score': score
    }


async def run_evaluation(
    session: Session,
    test_run_data: dict,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    broker=None,
):
    """Orquestra o processo de avaliação de testes."""
    
    test_collection_id = test_run_data.get('test_collection_id')
    if test_collection_id:
        test_collection_id = UUID(test_collection_id)
        
    test_case_id = test_run_data.get('test_case_id')
    if test_case_id:
        test_case_id = UUID(test_case_id)
        
    metric_ids = [UUID(m_id) for m_id in test_run_data['metric_ids']]
    
    model_id = test_run_data.get('model_id')
    if model_id:
        model_id = UUID(model_id)
    
    test_cases = []
    doc_id = None
    
    if test_case_id:
        # Execução de um caso de teste específico
        test_case = await evaluation_repository.get_test_case(session, test_case_id)
        if not test_case or test_case.deleted_at:
            raise ValueError("Test case not found")
        
        test_cases = [test_case]
        doc_id = test_case.doc_id
        
        # Se não foi passado collection_id, tenta pegar do caso de teste para manter consistência no TestRun
        if not test_collection_id:
            test_collection_id = test_case.test_collection_id
            
    elif test_collection_id:
        # Execução de toda a coleção
        test_collection = await evaluation_repository.get_test_collection(session, test_collection_id)
        if not test_collection or test_collection.deleted_at:
            raise ValueError("Test collection not found")
        
        test_cases = await evaluation_repository.get_test_cases(session, test_collection_id=test_collection_id)
        if not test_cases:
            raise ValueError("No test cases found for this collection")
    else:
        raise ValueError("Either test_collection_id or test_case_id must be provided")
    
    # Valida que todos os casos referenciam o mesmo documento (caso seja coleção)
    doc_ids = set(tc.doc_id for tc in test_cases if tc.doc_id)
    if len(doc_ids) > 1:
        raise ValueError("All test cases must reference the same document")
    
    if not doc_ids:
        raise ValueError("Test cases must have a document associated")
    
    doc_id = doc_ids.pop()
    
    # Cria test_run
    test_run_data_db = {
        'test_collection_id': test_collection_id,
        'created_by': current_user.id
    }
    test_run = await evaluation_repository.create_test_run(session, test_run_data_db, current_user)
    test_run_id = test_run.id
    
    # Processa documento (Flow completo: Upload -> RabbitMQ -> Processamento -> Vetores -> CheckTree)
    db_release = await releases_service.create_release(
        doc_id, session, current_user, file
    )

    print(f"1. Release created: {db_release.id}")
    
    # Publica evento no RabbitMQ para iniciar o processamento
    if broker:
        await broker.publish(db_release.id, 'releases_create_vectors')
    else:
        raise ValueError("Broker not available for publishing release event")
    
    # Aguarda processamento completo do release
    processed_release = await wait_for_release_processing(session, db_release.id)

    print(f"2. Release processed: {processed_release.id}")

    # Processa cada caso de teste
    results_summary = []
    
    for test_case in test_cases:
        for metric_id in metric_ids:
            try:
                result = await process_test_case(
                    session, 
                    test_case, 
                    metric_id, 
                    model_id, 
                    processed_release, 
                    test_run_id, 
                    current_user
                )
                results_summary.append(result)
            except Exception as e:
                logger.exception("Error processing test case %s", test_case.id)
                results_summary.append({
                    'test_case_id': str(test_case.id),
                    'metric_id': str(metric_id),
                    'error': str(e)
                })
    
    return {
        'test_run_id': str(test_run_id),
        'test_collection_id': str(test_collection_id) if test_collection_id else None,
        'case_count': len(test_cases),
        'metric_count': len(metric_ids),
        'results': results_summary
    }
