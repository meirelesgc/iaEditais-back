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
    TestRunExecute,
    TestRunExecutionResult,
    TestRunList,
    TestRunPublic,
)
from iaEditais.services import evaluation_service

router = APIRouter(
    prefix='/test-runs',
    tags=['avaliação, execução de testes'],
)


@router.get('/', response_model=TestRunList)
async def read_test_runs(
    session: Session,
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
async def read_test_run(test_run_id: UUID, session: Session):
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
    status_code=HTTPStatus.CREATED,
    response_model=TestRunExecutionResult,
)
async def execute_test_run(
    session: Session,
    current_user: CurrentUser,
    payload: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Executa uma bateria de testes.
    Payload deve ser um JSON compatível com TestRunExecute.
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

        print('DEBUG: Preparando dados para o service - Checkpoint 4')
        # Prepara dados para o service
        data_to_service = {
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
            'created_by': current_user.id,
        }

        print('DEBUG: Chamando evaluation_service.run_evaluation - Checkpoint 5')
        result = await evaluation_service.run_evaluation(
            session, data_to_service, current_user, file, router.broker
        )

        print('DEBUG: Test run executado com sucesso - Checkpoint 6')
        return result

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f'Invalid JSON in payload: {str(e)}',
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail=str(e)
        ) from e
    except TimeoutError as e:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_TIMEOUT, detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f'Internal server error: {str(e)}',
        ) from e

