from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from iaEditais.core.dependencies import Session
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    TestResultList,
    TestResultPublic,
)

router = APIRouter(
    prefix='/test-results',
    tags=['avaliação, resultados de testes'],
)


@router.get('/', response_model=TestResultList)
async def read_test_results(
    session: Session,
    filters: Annotated[FilterPage, Depends()],
    test_run_id: UUID = Query(..., description='ID do test run para filtrar os resultados'),
):
    """Lista todos os resultados de teste filtrados por test_run_id."""
    
    # Valida se o test_run existe
    test_run = await evaluation_repository.get_test_run(session, test_run_id)
    if not test_run or test_run.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test run not found',
        )
    
    test_results = await evaluation_repository.get_test_results(
        session, test_run_id, filters.offset, filters.limit
    )
    
    return {'test_results': test_results}


@router.get('/{test_result_id}', response_model=TestResultPublic)
async def read_test_result(test_result_id: UUID, session: Session):
    """Busca um resultado de teste por ID."""
    test_result = await evaluation_repository.get_test_result(session, test_result_id)

    if not test_result or test_result.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test result not found',
        )

    return test_result

