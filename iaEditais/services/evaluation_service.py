"""
Service para o módulo de Evaluation.

Contém a lógica de execução de testes usando DeepEval.
"""

import asyncio
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from fastapi import File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import (
    AppliedTaxonomy,
    AppliedTypification,
    DocumentRelease,
    Metric,
    User,
)
from iaEditais.repositories import evaluation_repository
from iaEditais.services import releases_service

logger = logging.getLogger(__name__)


async def wait_for_release_processing(
    session: AsyncSession, release_id: UUID
) -> DocumentRelease:
    """
    Aguarda o processamento do release ser concluído.
    Verifica se o campo 'description' foi preenchido, o que ocorre na etapa final.
    """
    print(f'DEBUG: Iniciando wait_for_release_processing para release {release_id} - Checkpoint 29')
    max_retries = 180  # 15 minutes (180 * 5s)
    for attempt in range(max_retries):
        # CRÍTICO: Expira todos os objetos da sessão para forçar busca no banco
        # Isso garante que vemos commits de outras sessões (do worker)
        session.expire_all()

        # Busca fresca do banco, ignorando qualquer cache
        stmt = (
            select(DocumentRelease)
            .where(DocumentRelease.id == release_id)
            .execution_options(
                populate_existing=True
            )  # Força refresh mesmo se já estiver na sessão
            .options(
                selectinload(DocumentRelease.check_tree)
                .selectinload(AppliedTypification.taxonomies)
                .selectinload(AppliedTaxonomy.branches)
            )
        )
        release = await session.scalar(stmt)

        # Debug: log periódico para monitorar
        if attempt % 12 == 0:  # A cada 1 minuto
            logger.info(
                'Waiting for release processing: attempt %d/%d, release_id=%s, has_description=%s',
                attempt + 1,
                max_retries,
                release_id,
                bool(release and release.description),
            )
            print(f'DEBUG: Tentativa {attempt + 1}/{max_retries} - Release {release_id} - Description presente: {bool(release and release.description)} - Checkpoint 30')

        if release and release.description:
            logger.info('Release processing completed: %s', release_id)
            print(f'DEBUG: Release {release_id} processado com sucesso! Description encontrado - Checkpoint 31')
            return release

        await asyncio.sleep(5)

    print(f'DEBUG: Timeout aguardando processamento do release {release_id} - Checkpoint 32')
    raise TimeoutError('Timeout waiting for release processing')


async def process_test_case(
    session: AsyncSession,
    test_case,
    metric_id: UUID,
    model_id: Optional[UUID],
    processed_release: DocumentRelease,
    test_run_id: UUID,
    current_user_id: UUID,
):
    """
    Executa a avaliação de um caso de teste utilizando DeepEval.
    Compara o resultado do processamento (AppliedBranch) com o esperado (TestCase).

    Args:
        current_user_id: UUID do usuário (não o objeto User, para evitar erro greenlet)
    """
    print(f'DEBUG: Iniciando process_test_case para caso {test_case.id} com métrica {metric_id} - Checkpoint 33')
    logger.info('Processing test case: %s', test_case.id)

    # 1. Busca Métrica
    print(f'DEBUG: Buscando métrica {metric_id} no banco - Checkpoint 34')
    metric_db = await session.get(Metric, metric_id)
    if not metric_db:
        raise ValueError(f'Metric {metric_id} not found')

    # 2. Recarrega o release com relacionamentos para garantir acesso assíncrono
    # CRÍTICO: Isso evita o erro "greenlet_spawn has not been called"
    # O objeto precisa ser recarregado na sessão atual para acessar relacionamentos
    print(f'DEBUG: Recarregando release {processed_release.id} com relacionamentos - Checkpoint 35')
    stmt = (
        select(DocumentRelease)
        .where(DocumentRelease.id == processed_release.id)
        .options(
            selectinload(DocumentRelease.check_tree)
            .selectinload(AppliedTypification.taxonomies)
            .selectinload(AppliedTaxonomy.branches)
        )
    )
    release_with_tree = await session.scalar(stmt)
    if not release_with_tree:
        raise ValueError(f'Release {processed_release.id} not found')

    # 3. Encontra o AppliedBranch correspondente ao TestCase
    print(f'DEBUG: Procurando AppliedBranch correspondente ao branch_id {test_case.branch_id} - Checkpoint 36')
    target_branch = None
    if test_case.branch_id:
        for typ in release_with_tree.check_tree:
            for tax in typ.taxonomies:
                for branch in tax.branches:
                    if branch.original_id == test_case.branch_id:
                        target_branch = branch
                        break
                if target_branch:
                    break
            if target_branch:
                break

    actual_output = 'Nenhum resultado gerado para este item.'
    if target_branch and target_branch.feedback:
        actual_output = target_branch.feedback

    # 4. Prepara LLMTestCase do DeepEval
    print(f'DEBUG: Preparando LLMTestCase do DeepEval - Checkpoint 37')
    llm_test_case = LLMTestCase(
        input=test_case.input or test_case.name,
        actual_output=actual_output,
        expected_output=test_case.expected_feedback,
    )

    # 5. Configura Métrica GEval
    print(f'DEBUG: Configurando métrica GEval - Checkpoint 38')
    eval_steps = []
    if metric_db.evaluation_steps:
        eval_steps = [
            step.strip()
            for step in metric_db.evaluation_steps.split('\n')
            if step.strip()
        ]

    metric = GEval(
        name=metric_db.name,
        criteria=metric_db.criteria,
        evaluation_steps=eval_steps,
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        model='gpt-4o-mini',
        threshold=metric_db.threshold or 0.5,
    )

    # 6. Executa Avaliação em thread separada
    # CRÍTICO: DeepEval usa nest_asyncio que corrompe o event loop do asyncio
    # Executar em thread separada isola o problema
    print('DEBUG: Executando avaliação com DeepEval em thread separada - Checkpoint 39')
    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            await loop.run_in_executor(executor, metric.measure, llm_test_case)
        score = metric.score
        reason = metric.reason
        passed = metric.is_successful()
        print(f'DEBUG: Avaliação concluída - Score: {score}, Passed: {passed} - Checkpoint 40')
    except Exception as e:
        logger.error('Error executing DeepEval metric: %s', e)
        print(f'DEBUG: Erro na avaliação DeepEval: {str(e)} - Checkpoint 41')
        score = 0.0
        reason = f'Error evaluating: {str(e)}'
        passed = False

    # 7. Salva Resultado
    print(f'DEBUG: Salvando resultado no banco de dados - Checkpoint 42')
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
        'passed_fulfilled': (
            (target_branch.fulfilled == test_case.expected_fulfilled)
            if target_branch
            else False
        ),
        'created_by': current_user_id,
    }

    result_id = await evaluation_repository.create_test_result(
        session, result_data
    )
    print(f'DEBUG: Resultado salvo com ID: {result_id} - Checkpoint 43')

    return {
        'test_case_id': str(test_case.id),
        'metric_id': str(metric_id),
        'test_result_id': str(result_id),
        'passed': passed,
        'score': score,
    }


async def run_evaluation(
    session: AsyncSession,
    test_run_data: dict,
    current_user: User,
    file: UploadFile = File(...),
    broker=None,
):
    """Orquestra o processo de avaliação de testes."""
    print('DEBUG: Iniciando run_evaluation - Checkpoint 7')

    print('DEBUG: Processando parâmetros de entrada - Checkpoint 8')
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

    print('DEBUG: Buscando casos de teste - Checkpoint 9')
    if test_case_id:
        # Execução de um caso de teste específico
        print(f'DEBUG: Executando caso de teste específico: {test_case_id} - Checkpoint 10')
        test_case = await evaluation_repository.get_test_case(
            session, test_case_id
        )
        if not test_case or test_case.deleted_at:
            raise ValueError('Test case not found')

        test_cases = [test_case]
        doc_id = test_case.doc_id

        # Se não foi passado collection_id, tenta pegar do caso de teste
        if not test_collection_id:
            test_collection_id = test_case.test_collection_id

    elif test_collection_id:
        # Execução de toda a coleção
        print(f'DEBUG: Executando coleção de testes: {test_collection_id} - Checkpoint 11')
        test_collection = await evaluation_repository.get_test_collection(
            session, test_collection_id
        )
        if not test_collection or test_collection.deleted_at:
            raise ValueError('Test collection not found')

        test_cases = await evaluation_repository.get_test_cases(
            session, test_collection_id=test_collection_id
        )
        if not test_cases:
            raise ValueError('No test cases found for this collection')
        print(f'DEBUG: Encontrados {len(test_cases)} casos de teste - Checkpoint 12')
    else:
        raise ValueError(
            'Either test_collection_id or test_case_id must be provided'
        )

    # Valida que todos os casos referenciam o mesmo documento
    print('DEBUG: Validando documentos dos casos de teste - Checkpoint 13')
    doc_ids = set(tc.doc_id for tc in test_cases if tc.doc_id)
    if len(doc_ids) > 1:
        raise ValueError('All test cases must reference the same document')

    if not doc_ids:
        raise ValueError('Test cases must have a document associated')

    doc_id = doc_ids.pop()
    print(f'DEBUG: Documento ID identificado: {doc_id} - Checkpoint 14')

    # CRÍTICO: Salva IDs antes do wait_for_release_processing
    # O session.expire_all() dentro de wait_for_release_processing expira todos os objetos
    # Precisamos salvar os IDs para recarregar depois
    test_case_ids = [tc.id for tc in test_cases]
    current_user_id = current_user.id
    print(f'DEBUG: IDs salvos - {len(test_case_ids)} test_cases, user_id: {current_user_id} - Checkpoint 14.1')

    # Cria test_run
    print('DEBUG: Criando test_run no banco de dados - Checkpoint 15')
    test_run_data_db = {
        'test_collection_id': test_collection_id,
        'created_by': current_user.id,
    }
    test_run = await evaluation_repository.create_test_run(
        session, test_run_data_db, current_user
    )
    test_run_id = test_run.id
    print(f'DEBUG: Test run criado com ID: {test_run_id} - Checkpoint 16')

    # Processa documento (Flow completo)
    print('DEBUG: Criando release do documento - Checkpoint 17')
    db_release = await releases_service.create_release(
        doc_id, session, current_user, file
    )

    logger.info('Release created: %s', db_release.id)
    print(f'DEBUG: Release criado com ID: {db_release.id} - Checkpoint 18')

    # Publica evento no RabbitMQ para iniciar o processamento
    print('DEBUG: Publicando evento no RabbitMQ para processamento - Checkpoint 19')
    if broker:
        await broker.publish(db_release.id, 'releases_create_vectors')
        print('DEBUG: Evento publicado no RabbitMQ - Checkpoint 20')
    else:
        raise ValueError('Broker not available for publishing release event')

    # Aguarda processamento completo do release
    print('DEBUG: Aguardando processamento completo do release - Checkpoint 21')
    processed_release = await wait_for_release_processing(
        session, db_release.id
    )

    logger.info('Release processed: %s', processed_release.id)
    print(f'DEBUG: Release processado com sucesso: {processed_release.id} - Checkpoint 22')

    # CRÍTICO: Recarrega test_cases após wait_for_release_processing
    # O session.expire_all() expirou todos os objetos, precisamos recarregar
    print('DEBUG: Recarregando test_cases após expire_all - Checkpoint 22.1')
    test_cases = []
    for tc_id in test_case_ids:
        tc = await evaluation_repository.get_test_case(session, tc_id)
        if tc:
            test_cases.append(tc)
    print(f'DEBUG: {len(test_cases)} test_cases recarregados - Checkpoint 22.2')

    # Processa cada caso de teste
    print(f'DEBUG: Iniciando processamento de {len(test_cases)} casos de teste com {len(metric_ids)} métricas - Checkpoint 23')
    results_summary = []

    for idx, test_case in enumerate(test_cases, 1):
        print(f'DEBUG: Processando caso de teste {idx}/{len(test_cases)}: {test_case.id} - Checkpoint 24')
        for metric_idx, metric_id in enumerate(metric_ids, 1):
            print(f'DEBUG: Processando métrica {metric_idx}/{len(metric_ids)}: {metric_id} para caso {test_case.id} - Checkpoint 25')
            try:
                result = await process_test_case(
                    session,
                    test_case,
                    metric_id,
                    model_id,
                    processed_release,
                    test_run_id,
                    current_user_id,
                )
                results_summary.append(result)
                print(f'DEBUG: Caso de teste {test_case.id} com métrica {metric_id} processado com sucesso - Checkpoint 26')
            except Exception as e:
                logger.exception('Error processing test case %s', test_case.id)
                print(f'DEBUG: Erro ao processar caso {test_case.id} com métrica {metric_id}: {str(e)} - Checkpoint 27')
                results_summary.append({
                    'test_case_id': str(test_case.id),
                    'metric_id': str(metric_id),
                    'error': str(e),
                })

    print(f'DEBUG: Processamento completo. Total de resultados: {len(results_summary)} - Checkpoint 28')
    return {
        'test_run_id': str(test_run_id),
        'test_collection_id': (
            str(test_collection_id) if test_collection_id else None
        ),
        'case_count': len(test_cases),
        'metric_count': len(metric_ids),
        'results': results_summary,
    }

