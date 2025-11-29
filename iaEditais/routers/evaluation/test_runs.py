from http import HTTPStatus
import json
from fastapi import File, HTTPException, UploadFile, Form
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import TestRunExecutionResult, TestRunExecute
from iaEditais.services import evaluation_service

router = APIRouter(
    prefix='/test-runs',
    tags=['avaliação, execução de testes'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TestRunExecutionResult,
)
async def execute_test_run(
    session: Session,
    current_user: CurrentUser,
    payload: str = Form(...),  # Recebe como string do form-data
    file: UploadFile = File(...),
):
    """
    Executa uma bateria de testes.
    Payload deve ser um JSON compatível com TestRunExecute.
    """
    try:
        test_run_data_dict = json.loads(payload)
        
        # Validação via Pydantic
        try:
            test_run_execute = TestRunExecute(**test_run_data_dict)
        except Exception as e:
            raise ValueError(f"Invalid payload structure: {e}") from e

        if not test_run_execute.test_collection_id and not test_run_execute.test_case_id:
            raise ValueError("Either test_collection_id or test_case_id is required")
        
        # Prepara dados para o service (convertendo UUIDs para strings conforme esperado pelo service)
        data_to_service = {
            'test_collection_id': str(test_run_execute.test_collection_id) if test_run_execute.test_collection_id else None,
            'test_case_id': str(test_run_execute.test_case_id) if test_run_execute.test_case_id else None,
            'metric_ids': [str(m) for m in test_run_execute.metric_ids],
            'model_id': str(test_run_execute.model_id) if test_run_execute.model_id else None,
            'created_by': current_user.id
        }
        
        result = await evaluation_service.run_evaluation(
            session, data_to_service, current_user, file, router.broker
        )
        
        return result
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid JSON in payload: {str(e)}"
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        ) from e
    except TimeoutError as e:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_TIMEOUT,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) from e
