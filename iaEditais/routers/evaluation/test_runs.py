from http import HTTPStatus
import json
from fastapi import File, HTTPException, UploadFile, Form
from faststream.rabbit.fastapi import RabbitRouter as APIRouter

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import TestRunExecutionResult
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
    """
    try:
        test_run_data_dict = json.loads(payload)
        
        # Validação
        if 'test_id' not in test_run_data_dict:
            raise HTTPException(status_code=400, detail="test_id is required")
        if 'case_metric_ids' not in test_run_data_dict:
            raise HTTPException(status_code=400, detail="case_metric_ids is required")
        
        test_run_data_dict['created_by'] = current_user.id
        
        result = await evaluation_service.run_evaluation(
            session, test_run_data_dict, current_user, file, router.broker
        )
        
        return result
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid JSON in payload: {str(e)}"
        )
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
