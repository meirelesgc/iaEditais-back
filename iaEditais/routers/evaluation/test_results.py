"""
Rotas para consulta de resultados de testes (TestResult).
"""

from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from iaEditais.core.dependencies import CurrentUser, Session
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
    current_user: CurrentUser,
    filters: Annotated[FilterPage, Depends()],
    test_run_id: Optional[UUID] = Query(
        None, description='ID do test run para filtrar os resultados (opcional)'
    ),
):
    """Lista todos os resultados de teste, opcionalmente filtrados por test_run_id."""

    # Valida se o test_run existe (apenas se test_run_id foi fornecido)
    if test_run_id:
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
async def read_test_result(
    test_result_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Busca um resultado de teste por ID."""
    test_result = await evaluation_repository.get_test_result(
        session, test_result_id
    )

    if not test_result or test_result.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test result not found',
        )

    return test_result

