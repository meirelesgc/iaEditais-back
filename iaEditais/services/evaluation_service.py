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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.models import (
    AIModel,
    AppliedTaxonomy,
    AppliedTypification,
    Branch,
    DocumentRelease,
    Metric,
    TestCase,
)
from iaEditais.repositories import evaluation_repository

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
    test_case_id: UUID,
    metric_id: UUID,
    model_id: Optional[UUID],
    release_id: UUID,
    test_run_id: UUID,
    current_user_id: UUID,
):
    """
    Executa a avaliação de um caso de teste utilizando DeepEval.
    Compara o resultado do processamento (AppliedBranch) com o esperado (TestCase).

    Args:
        test_case_id: UUID do test case (não o objeto, para evitar erro greenlet)
        release_id: UUID do release (não o objeto, para evitar erro greenlet)
        current_user_id: UUID do usuário (não o objeto User, para evitar erro greenlet)
    """
    print(f'DEBUG: Iniciando process_test_case para caso {test_case_id} com métrica {metric_id} - Checkpoint 33')
    logger.info('Processing test case: %s', test_case_id)

    # 0. Recarrega test_case na sessão atual para evitar erro greenlet
    test_case = await session.get(TestCase, test_case_id)
    if not test_case:
        raise ValueError(f'TestCase {test_case_id} not found')

    # 1. Busca Métrica
    print(f'DEBUG: Buscando métrica {metric_id} no banco - Checkpoint 34')
    metric_db = await session.get(Metric, metric_id)
    if not metric_db:
        raise ValueError(f'Metric {metric_id} not found')

    # 1.5 Busca AIModel se model_id foi passado
    model_code_name = 'gpt-4o-mini'  # Default
    if model_id:
        ai_model = await session.get(AIModel, model_id)
        if ai_model:
            model_code_name = ai_model.code_name
            print(f'DEBUG: Usando modelo {model_code_name} - Checkpoint 34.1')
        else:
            print(f'DEBUG: AIModel {model_id} não encontrado, usando default {model_code_name} - Checkpoint 34.2')
    else:
        print(f'DEBUG: model_id não informado, usando default {model_code_name} - Checkpoint 34.3')

    # 2. Recarrega o release com relacionamentos para garantir acesso assíncrono
    # CRÍTICO: Isso evita o erro "greenlet_spawn has not been called"
    # O objeto precisa ser recarregado na sessão atual para acessar relacionamentos
    print(f'DEBUG: Recarregando release {release_id} com relacionamentos - Checkpoint 35')
    stmt = (
        select(DocumentRelease)
        .where(DocumentRelease.id == release_id)
        .options(
            selectinload(DocumentRelease.check_tree)
            .selectinload(AppliedTypification.taxonomies)
            .selectinload(AppliedTaxonomy.branches)
        )
    )
    release_with_tree = await session.scalar(stmt)
    if not release_with_tree:
        raise ValueError(f'Release {release_id} not found')

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

    # Busca o Branch original para obter o título
    branch_title = test_case.name  # fallback
    if test_case.branch_id:
        branch = await session.get(Branch, test_case.branch_id)
        if branch:
            branch_title = branch.title
            print(f'DEBUG: Branch encontrado - título: {branch_title} - Checkpoint 37.1')

    input_text = f"Faça uma análise e verifique se o critério '{branch_title}' está sendo atendido nesse edital"

    llm_test_case = LLMTestCase(
        input=input_text,
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
        model=model_code_name,
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
        'input': input_text,
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
