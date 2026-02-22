"""
Worker para processamento assíncrono de test runs.
"""

import logging
from uuid import UUID

from faststream.rabbit import RabbitRouter

from iaEditais.core.dependencies import CacheManager, Model, Session, VStore
from iaEditais.models import TestRun, User
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import TestRunPublic, TestRunStatus, WSMessage
from iaEditais.services import evaluation_service

logger = logging.getLogger(__name__)
router = RabbitRouter()


async def send_test_run_update(
    manager: CacheManager,
    session,
    test_run_id: UUID,
    status: str,
    progress: str = None,
    error_message: str = None,
):
    """Envia atualização de progresso via WebSocket com payload completo."""
    # Busca TestRun atualizado do banco
    test_run = await session.get(TestRun, test_run_id)
    if test_run:
        test_run_public = TestRunPublic.model_validate(test_run)
        payload = test_run_public.model_dump(mode='json')
        # Adiciona campos extras de progresso
        payload['progress'] = progress
        payload['error_message'] = error_message
    else:
        payload = {
            'test_run_id': str(test_run_id),
            'status': status,
            'progress': progress,
            'error_message': error_message,
        }
    
    ws_message = WSMessage(
        event='test_run.update',
        message=status,
        payload=payload,
    )
    manager.broadcast(ws_message)
    print(f'DEBUG: WebSocket - test_run.update: {status} - {progress}')


@router.subscriber('test_run_process')
async def process_test_run(
    payload: dict,
    session: Session,
    vectorstore: VStore,
    model: Model,
    manager: CacheManager,
):
    """
    Processa um test run de forma assíncrona.
    
    Payload esperado:
    {
        'test_run_id': str,
        'test_collection_id': str | None,
        'test_case_id': str | None,
        'metric_ids': list[str],
        'model_id': str | None,
        'doc_id': str,
        'file_path': str,
        'created_by': str,
    }
    """
    print(f'DEBUG: Worker - Iniciando processamento de test_run - Checkpoint W1')
    print(f'DEBUG: Payload recebido: {payload}')
    
    test_run_id = UUID(payload['test_run_id'])
    test_collection_id = (
        UUID(payload['test_collection_id']) 
        if payload.get('test_collection_id') 
        else None
    )
    test_case_id = (
        UUID(payload['test_case_id']) 
        if payload.get('test_case_id') 
        else None
    )
    metric_ids = [UUID(m) for m in payload.get('metric_ids', [])]
    model_id = UUID(payload['model_id']) if payload.get('model_id') else None
    doc_id = UUID(payload['doc_id'])
    file_path = payload['file_path']  # Mantém como string para o banco de dados
    created_by_id = UUID(payload['created_by'])
    
    try:
        # 1. Atualiza status para TestRunStatus.PROCESSING.value
        print('DEBUG: Worker - Atualizando status para processing - Checkpoint W2')
        await evaluation_repository.update_test_run_status(
            session, test_run_id, TestRunStatus.PROCESSING.value, 'Iniciando processamento...'
        )
        await send_test_run_update(
            manager, session, test_run_id, TestRunStatus.PROCESSING.value, 'Iniciando processamento...'
        )
        
        # 2. Busca usuário
        print(f'DEBUG: Worker - Buscando usuário {created_by_id} - Checkpoint W3')
        current_user = await session.get(User, created_by_id)
        if not current_user:
            raise ValueError(f'User {created_by_id} not found')
        
        # 3. Busca test cases
        print('DEBUG: Worker - Buscando test cases - Checkpoint W4')
        test_cases = []
        
        if test_case_id:
            test_case = await evaluation_repository.get_test_case(
                session, test_case_id
            )
            if not test_case or test_case.deleted_at:
                raise ValueError('Test case not found')
            test_cases = [test_case]
        elif test_collection_id:
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
        
        print(f'DEBUG: Worker - Encontrados {len(test_cases)} test cases - Checkpoint W5')
        
        # doc_id agora vem do payload (criado na rota de test_runs)
        print(f'DEBUG: Worker - Documento ID (do payload): {doc_id} - Checkpoint W6')
        
        # Salva IDs antes do processamento
        test_case_ids = [tc.id for tc in test_cases]
        
        # 5. Cria release do documento
        print('DEBUG: Worker - Criando release do documento - Checkpoint W7')
        await evaluation_repository.update_test_run_status(
            session, test_run_id, TestRunStatus.PROCESSING.value, 'Criando release do documento...'
        )
        await send_test_run_update(
            manager, session, test_run_id, TestRunStatus.PROCESSING.value, 'Criando release do documento...'
        )
        
        from iaEditais.repositories import releases_repository
        
        # Busca documento e cria release
        db_doc = await releases_repository.get_db_doc(doc_id, session)
        if not db_doc:
            raise ValueError('Document not found')
        if not db_doc.history:
            raise ValueError('Document does not have a history')
        if len(db_doc.typifications) == 0:
            raise ValueError('There are no associated typifications')
        
        latest_history = db_doc.history[0]
        db_release = await releases_repository.insert_db_release(
            latest_history, file_path, session, current_user, is_test=True
        )
        # CRÍTICO: Salva o ID antes de qualquer expire para evitar erro greenlet
        release_id = db_release.id
        print(f'DEBUG: Worker - Release criado: {release_id} - Checkpoint W8')
        
        # Atualiza test_run com release_id
        await evaluation_repository.update_test_run_status(
            session, test_run_id, TestRunStatus.PROCESSING.value, 
            'Processando documento...', release_id=release_id
        )
        
        # 6. Publica para processamento de vetores
        await router.broker.publish(db_release.id, 'release_pipeline')
        print('DEBUG: Worker - Publicado para release_pipeline - Checkpoint W9')
        
        await send_test_run_update(
            manager, session, test_run_id, TestRunStatus.PROCESSING.value, 'Processando documento (vetores)...'
        )
        
        # 7. Aguarda processamento completo do release
        print('DEBUG: Worker - Aguardando processamento do release - Checkpoint W10')
        await evaluation_service.wait_for_release_processing(
            session, release_id
        )
        print(f'DEBUG: Worker - Release processado: {release_id} - Checkpoint W11')
        
        # 8. Atualiza status para TestRunStatus.EVALUATING.value
        await evaluation_repository.update_test_run_status(
            session, test_run_id, TestRunStatus.EVALUATING.value, 
            f'Avaliando casos de teste (0/{len(test_case_ids)})...'
        )
        await send_test_run_update(
            manager, session, test_run_id, TestRunStatus.EVALUATING.value, 
            f'Avaliando casos de teste (0/{len(test_case_ids)})...'
        )
        
        # 9. Recarrega test_cases após wait_for_release_processing
        # CRÍTICO: Extrai IDs imediatamente para evitar erro greenlet após commits
        print('DEBUG: Worker - Recarregando test_cases - Checkpoint W12')
        test_case_id_list = []
        for tc_id in test_case_ids:
            tc = await evaluation_repository.get_test_case(session, tc_id)
            if tc:
                # Extrai ID imediatamente antes de qualquer commit
                test_case_id_list.append(tc.id)
        
        # 10. Processa cada caso de teste
        print(f'DEBUG: Worker - Processando {len(test_case_id_list)} casos com {len(metric_ids)} métricas - Checkpoint W13')
        results_summary = []
        total_evaluations = len(test_case_id_list) * len(metric_ids)
        current_evaluation = 0
        
        for idx, test_case_id_current in enumerate(test_case_id_list, 1):
            # test_case_id_current já é UUID, não precisa acessar .id
            for metric_idx, metric_id in enumerate(metric_ids, 1):
                current_evaluation += 1
                progress_msg = f'Avaliando ({current_evaluation}/{total_evaluations})...'
                
                await evaluation_repository.update_test_run_status(
                    session, test_run_id, TestRunStatus.EVALUATING.value, progress_msg
                )
                await send_test_run_update(
                    manager, session, test_run_id, TestRunStatus.EVALUATING.value, progress_msg
                )
                
                print(f'DEBUG: Worker - Processando caso {idx}/{len(test_case_id_list)}, métrica {metric_idx}/{len(metric_ids)} - Checkpoint W14')
                
                try:
                    result = await evaluation_service.process_test_case(
                        session,
                        test_case_id_current,
                        metric_id,
                        model_id,
                        release_id,
                        test_run_id,
                        created_by_id,  # Usa UUID direto ao invés de current_user.id
                    )
                    results_summary.append({
                        'test_case_id': str(test_case_id_current),
                        'metric_id': str(metric_id),
                        'status': 'success',
                        'score': result.get('score') if isinstance(result, dict) else None,
                    })
                except Exception as e:
                    logger.error(
                        f'Error processing test case {test_case_id_current} with metric {metric_id}: {e}'
                    )
                    print(f'DEBUG: Worker - Erro no caso {test_case_id_current}: {e} - Checkpoint W15')
                    results_summary.append({
                        'test_case_id': str(test_case_id_current),
                        'metric_id': str(metric_id),
                        'status': TestRunStatus.ERROR.value,
                        'error': str(e),
                    })
        
        # 11. Atualiza status para TestRunStatus.COMPLETED.value
        print('DEBUG: Worker - Finalizando test run - Checkpoint W16')
        await evaluation_repository.update_test_run_status(
            session, test_run_id, TestRunStatus.COMPLETED.value, 
            f'Concluído: {len(results_summary)} avaliações processadas'
        )
        await send_test_run_update(
            manager, session, test_run_id, TestRunStatus.COMPLETED.value, 
            f'Concluído: {len(results_summary)} avaliações processadas'
        )
        
        print(f'DEBUG: Worker - Test run {test_run_id} concluído com sucesso - Checkpoint W17')
        
        return {
            'status': TestRunStatus.COMPLETED.value,
            'test_run_id': str(test_run_id),
            'evaluations': len(results_summary),
        }
        
    except Exception as e:
        logger.error(f'Error processing test run {test_run_id}: {e}')
        print(f'DEBUG: Worker - Erro fatal no test run {test_run_id}: {e} - Checkpoint W-ERROR')
        
        # Atualiza status para ERROR
        try:
            await evaluation_repository.update_test_run_status(
                session, test_run_id, TestRunStatus.ERROR.value, error_message=str(e)
            )
            await send_test_run_update(
                manager, session, test_run_id, TestRunStatus.ERROR.value, error_message=str(e)
            )
        except Exception as update_error:
            logger.error(f'Failed to update test run status: {update_error}')
            print(f'DEBUG: Worker - Erro ao atualizar status: {update_error}')
        
        return {
            'status': TestRunStatus.ERROR.value,
            'test_run_id': str(test_run_id),
            'error': str(e),
        }

