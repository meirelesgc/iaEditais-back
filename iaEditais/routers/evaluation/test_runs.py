"""
Rotas para execução de testes (TestRun).
"""

import json
from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, File, Form, HTTPException, Query, UploadFile
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    TestRunAccepted,
    TestRunExecute,
    TestRunList,
    TestRunPublic,
)
from iaEditais.services import storage_service

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'

router = APIRouter(
    prefix='/test-runs',
    tags=['avaliação, execução de testes'],
)


@router.get('/', response_model=TestRunList)
async def read_test_runs(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[FilterPage, Depends()],
    test_case_id: Optional[UUID] = Query(
        None, description='ID do test case para filtrar os test runs'
    ),
):
    """Lista todos os test runs, opcionalmente filtrados por test_case_id."""
    test_runs = await evaluation_repository.get_test_runs(
        session, test_case_id, filters.offset, filters.limit
    )
    return {'test_runs': test_runs}


@router.get('/{test_run_id}', response_model=TestRunPublic)
async def read_test_run(
    test_run_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Busca um test run por ID."""
    test_run = await evaluation_repository.get_test_run(session, test_run_id)

    if not test_run or test_run.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test run not found',
        )

    return test_run


@router.post(
    '/',
    status_code=HTTPStatus.ACCEPTED,
    response_model=TestRunAccepted,
)
async def execute_test_run(
    session: Session,
    current_user: CurrentUser,
    payload: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Inicia uma bateria de testes de forma assíncrona.
    Payload deve ser um JSON compatível com TestRunExecute.
    Retorna imediatamente com status 202 Accepted e o ID do test run.
    O processamento ocorre em background via worker.
    """
    print('DEBUG: Iniciando execução de test run - Checkpoint 1')
    try:
        print('DEBUG: Parseando payload JSON - Checkpoint 2')
        test_run_data_dict = json.loads(payload)

        # Validação via Pydantic
        try:
            print('DEBUG: Validando estrutura do payload - Checkpoint 3')
            test_run_execute = TestRunExecute(**test_run_data_dict)
        except Exception as e:
            raise ValueError(f'Invalid payload structure: {e}') from e

        if (
            not test_run_execute.test_collection_id
            and not test_run_execute.test_case_id
        ):
            raise ValueError(
                'Either test_collection_id or test_case_id is required'
            )

        # Salva arquivo para processamento posterior
        print('DEBUG: Salvando arquivo para processamento posterior - Checkpoint 4')
        file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)
        print(f'DEBUG: Arquivo salvo em: {file_path} - Checkpoint 4.1')

        # Cria test_run com status 'pending'
        print('DEBUG: Criando test_run com status pending - Checkpoint 5')
        test_run_data_db = {
            'test_collection_id': test_run_execute.test_collection_id,
            'test_case_id': test_run_execute.test_case_id,
            'status': 'pending',
        }
        test_run = await evaluation_repository.create_test_run(
            session, test_run_data_db, current_user
        )
        print(f'DEBUG: Test run criado com ID: {test_run.id} - Checkpoint 6')

        # Prepara dados para o worker
        worker_payload = {
            'test_run_id': str(test_run.id),
            'test_collection_id': (
                str(test_run_execute.test_collection_id)
                if test_run_execute.test_collection_id
                else None
            ),
            'test_case_id': (
                str(test_run_execute.test_case_id)
                if test_run_execute.test_case_id
                else None
            ),
            'metric_ids': [str(m) for m in test_run_execute.metric_ids],
            'model_id': (
                str(test_run_execute.model_id)
                if test_run_execute.model_id
                else None
            ),
            'file_path': str(file_path),
            'created_by': str(current_user.id),
        }

        # Publica no RabbitMQ para processamento assíncrono
        print('DEBUG: Publicando no RabbitMQ para processamento - Checkpoint 7')
        await router.broker.publish(worker_payload, 'test_run_process')
        print('DEBUG: Mensagem publicada no RabbitMQ - Checkpoint 8')

        return TestRunAccepted(
            test_run_id=test_run.id,
            status='pending',
            message='Test run iniciado. Acompanhe o progresso via WebSocket.',
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Invalid JSON in payload: {str(e)}',
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        print(f'DEBUG: Erro na execução: {str(e)} - Checkpoint ERROR')
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f'Internal server error: {str(e)}',
        ) from e

