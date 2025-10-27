import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated, Any, Dict
from uuid import UUID

from fastapi import Depends, File, UploadFile
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.core.database import get_session
from iaEditais.core.llm import get_model
from iaEditais.core.security import get_current_user
from iaEditais.models import (
    DocumentRelease,
    TestCase,
    TestCaseMetric,
    User,
)
from iaEditais.repositories import evaluation_repository
from iaEditais.services import releases_service

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
Model = Annotated[BaseChatModel, Depends(get_model)]


async def run_evaluation(
    session: Session,
    test_run_data: dict,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    broker=None,
):
    """Orquestra o processo de avaliação de testes."""
    
    test_id = UUID(test_run_data['test_id'])
    case_metric_ids = test_run_data['case_metric_ids']
    
    # Validações iniciais
    test = await evaluation_repository.get_test(session, test_id)
    if not test or test.deleted_at:
        raise ValueError("Test not found")
    
    # Valida todos os test_case_metric_ids e verifica doc_id
    doc_ids = set()
    for case_metric_id in case_metric_ids:
        tcm = await evaluation_repository.get_test_case_metric(session, case_metric_id)
        
        if not tcm or tcm.deleted_at or tcm.test_id != test_id:
            raise ValueError(f"Invalid test_case_metric_id: {case_metric_id}")
        
        test_case = await evaluation_repository.get_test_case(session, tcm.test_case_id)
        doc_ids.add(test_case.doc_id)
    
    # Valida que todos os casos referenciam o mesmo documento
    if len(doc_ids) > 1:
        raise ValueError("All test cases must reference the same document")
    
    doc_id = doc_ids.pop()
    
    # Cria test_run
    test_run = await evaluation_repository.create_test_run(session, test_run_data, current_user)
    test_run_id = test_run.id
    
    # Cria test_run_cases
    test_run_cases = await evaluation_repository.create_test_run_cases(
        session, test_run_id, case_metric_ids, test_id, current_user
    )
    
    # Extrai IDs de test_run_cases antes do polling
    test_run_cases_data = []
    for trc in test_run_cases:
        test_run_cases_data.append({
            'id': trc.id,
            'test_case_metric_id': trc.test_case_metric_id
        })
    
    # Processa documento
    db_release = await releases_service.create_release(
        doc_id, session, current_user, file
    )
    
    # Publica evento no RabbitMQ
    if broker:
        await broker.publish(db_release.id, 'releases_create_vectors')
    else:
        raise ValueError("Broker not available for publishing release event")
    
    # Aguarda processamento do release
    processed_release = await wait_for_release_processing(session, db_release.id)

    # Processa cada caso de teste
    results_summary = []
    
    for i, trc_data in enumerate(test_run_cases_data):
        try:
            tcm = await evaluation_repository.get_test_case_metric(session, trc_data['test_case_metric_id'])
            test_case = await evaluation_repository.get_test_case(session, tcm.test_case_id)
            
            result = await process_test_case(
                session, test_case, tcm, processed_release, trc_data['id'], current_user
            )
            results_summary.append(result)
            
        except Exception as e:
            results_summary.append({
                'test_case_id': str(trc_data['test_case_metric_id']),
                'error': str(e)
            })
    
    test_run_id_str = str(test_run_id)
    test_id_str = str(test_id)
    
    return {
        'test_run_id': test_run_id_str,
        'test_id': test_id_str,
        'case_count': len(case_metric_ids),
        'results': results_summary
    }


async def process_test_case(
    session: Session,
    test_case: TestCase,
    test_case_metric: TestCaseMetric,
    processed_release: DocumentRelease,
    test_run_case_id: UUID,
    current_user: CurrentUser,
):
    """Processa um caso de teste individual."""
    
    # Extrai atributos para evitar lazy load
    test_case_branch_id = test_case.branch_id
    test_case_id = test_case.id
    test_case_expected_fulfilled = test_case.expected_fulfilled
    test_case_metric_metric_id = test_case_metric.metric_id
    test_case_name = test_case.name
    test_case_expected_feedback = test_case.expected_feedback
    
    # Busca branch associada
    branch = await evaluation_repository.get_branch_by_name_or_id(session, test_case_branch_id)
    if not branch:
        raise ValueError(f"Branch not found for test_case {test_case_id}")
    
    branch_id = branch.id
    
    # Extrai evaluation da branch processada
    branch_evaluation = extract_branch_evaluation(processed_release, branch_id)
    
    # Busca a métrica e extrai atributos
    try:
        metric = await evaluation_repository.get_metric(session, test_case_metric_metric_id)
        if not metric:
            raise ValueError(f"Metric {test_case_metric_metric_id} not found")
        
        metric_name = metric.name
        metric_criteria = metric.criteria
        metric_evaluation_steps = metric.evaluation_steps
        metric_threshold = metric.threshold or 0.5
        metric_model_id = metric.model_id
    except asyncio.CancelledError:
        raise
    except Exception as e:
        return {
            'test_case_id': str(test_case_id),
            'error': f"Metric not found: {str(e)}"
        }
    
    # Executa avaliação com DeepEval
    evaluation_result = await evaluate_with_metrics(
        test_case_name=test_case_name,
        test_case_expected_feedback=test_case_expected_feedback,
        metric_name=metric_name,
        metric_criteria=metric_criteria,
        metric_evaluation_steps=metric_evaluation_steps,
        metric_threshold=metric_threshold,
        branch_evaluation=branch_evaluation
    )
    
    # Calcula comparação dos booleanos
    actual_fulfilled = branch_evaluation.get('fulfilled', False)
    expected_fulfilled = test_case_expected_fulfilled
    passed_fulfilled = actual_fulfilled == expected_fulfilled
    
    # Salva resultado
    test_result_data = {
        'test_run_case_id': test_run_case_id,
        'model_id': metric_model_id,
        'threshold_used': evaluation_result.get('threshold'),
        'reason_feedback': evaluation_result.get('reasoning'),
        'score_feedback': evaluation_result.get('score'),
        'passed_feedback': evaluation_result.get('passed'),
        'actual_feedback': branch_evaluation.get('feedback'),
        'actual_fulfilled': actual_fulfilled,
        'passed_fulfilled': passed_fulfilled,
    }
    
    result_id = await evaluation_repository.create_test_result(session, test_result_data, current_user)
    result_id_str = str(result_id)
    test_case_id_str = str(test_case_id)
    metric_id_str = str(test_case_metric_metric_id)
    
    return {
        'test_case_id': test_case_id_str,
        'metric_id': metric_id_str,
        'result_id': result_id_str,
        'score': evaluation_result.get('score'),
        'passed': evaluation_result.get('passed'),
        'actual_fulfilled': actual_fulfilled,
        'expected_fulfilled': expected_fulfilled,
        'passed_fulfilled': passed_fulfilled
    }


async def wait_for_release_processing(session: Session, release_id: UUID, max_attempts: int = 60):
    """Aguarda o processamento de um release com polling."""
    
    attempt = 0
    
    while attempt < max_attempts:
        await asyncio.sleep(5)
        
        # Expira o cache da sessão para buscar dados atualizados
        session.expire_all()
        
        # Busca o release atualizado com eager loading
        query = select(DocumentRelease).options(
            selectinload(DocumentRelease.check_tree)
        ).where(
            DocumentRelease.id == release_id,
            DocumentRelease.deleted_at.is_(None)
        )
        updated_release = await session.scalar(query)
        
        if updated_release and updated_release.check_tree:
            if len(updated_release.check_tree) > 0:
                return updated_release
        
        attempt += 1
    
    raise TimeoutError(f"Release processing timeout after {max_attempts} attempts")


def extract_branch_evaluation(release: DocumentRelease, branch_id: UUID) -> Dict:
    """Extrai a avaliação de uma branch específica do release processado."""
    
    # Navega pela estrutura do release para encontrar a branch
    for typification in release.check_tree:
        for taxonomy in typification.taxonomies:
            for branch in taxonomy.branches:
                if branch.original_id == branch_id:
                    return {
                        'feedback': branch.feedback,
                        'fulfilled': branch.fulfilled,
                        'score': branch.score,
                    }
    
    # Se não encontrou, retorna valores padrão
    return {
        'feedback': 'Branch evaluation not found',
        'fulfilled': False,
        'score': 0,
    }


async def evaluate_with_metrics(
    test_case_name: str,
    test_case_expected_feedback: str,
    metric_name: str,
    metric_criteria: str,
    metric_evaluation_steps: Any,
    metric_threshold: float,
    branch_evaluation: Dict,
):
    """Executa avaliação usando deepeval com métricas."""
    
    try:
        from deepeval.test_case import LLMTestCase, LLMTestCaseParams
        from deepeval.metrics import GEval
        from deepeval import evaluate
        
        llm_test_case = LLMTestCase(
            input=f"Avaliar critério: {test_case_name}",
            actual_output=branch_evaluation.get('feedback', ''),
            expected_output=test_case_expected_feedback or ''
        )
        
        # Cria métrica
        evaluation_steps = []
        if metric_evaluation_steps:
            if isinstance(metric_evaluation_steps, str):
                evaluation_steps = [step.strip() for step in metric_evaluation_steps.split('\n') if step.strip()]
            else:
                evaluation_steps = metric_evaluation_steps
        
        precision_metric = GEval(
            name=metric_name,
            criteria=metric_criteria,
            evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
            evaluation_steps=evaluation_steps
        )
        
        # Executa avaliação em thread separada para não bloquear event loop
        loop = asyncio.get_event_loop()
        
        def run_deepeval():
            """Wrapper síncrono para DeepEval"""
            return evaluate(
                test_cases=[llm_test_case], 
                metrics=[precision_metric]
            )
        
        with ThreadPoolExecutor(max_workers=1) as executor:
            result = await loop.run_in_executor(executor, run_deepeval)
        
        # Extrai dados do resultado
        test_results_list = result.test_results
        
        if test_results_list:
            test_result = test_results_list[0]
            metric_data = test_result.metrics_data[0] if test_result.metrics_data else None
            return {
                'score': metric_data.score if metric_data else 0.0,
                'passed': test_result.success,
                'reasoning': metric_data.reason if metric_data else 'No reasoning provided',
                'threshold': metric_threshold,
                'metric_name': metric_name
            }
        
        return {
            'score': 0.0,
            'passed': False,
            'reasoning': 'No evaluation result',
            'threshold': metric_threshold,
            'metric_name': metric_name
        }
        
    except Exception as e:
        return {
            'score': 0.0,
            'passed': False,
            'reasoning': f'Evaluation error: {str(e)}',
            'threshold': metric_threshold,
            'metric_name': metric_name
        }


async def create_llm_test_case(test_case: TestCase, branch_evaluation: Dict) -> Dict:
    """Monta um caso de teste para deepeval."""
    
    return {
        'input': f"Avaliar critério: {test_case.name}",
        'actual_output': branch_evaluation.get('feedback', ''),
        'expected_output': test_case.expected_feedback or '',
        'expected_fulfilled': test_case.expected_fulfilled,
        'actual_fulfilled': branch_evaluation.get('fulfilled', False)
    }
