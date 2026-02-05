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
    SortBy,
    SortOrder,
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
    test_case_id: Optional[UUID] = Query(
        None, description='ID do test case para filtrar os resultados (opcional)'
    ),
    metric_id: Optional[UUID] = Query(
        None, description='ID da métrica para filtrar os resultados (opcional)'
    ),
    model_id: Optional[UUID] = Query(
        None, description='ID do modelo para filtrar os resultados (opcional)'
    ),
    sort_by: SortBy = Query(
        SortBy.CREATED_AT,
        description='Campo para ordenação (created_at ou updated_at)',
    ),
    sort_order: SortOrder = Query(
        SortOrder.DESC,
        description='Direção da ordenação (asc ou desc)',
    ),
):
    """Lista todos os resultados de teste com filtros opcionais."""

    if test_run_id:
        test_run = await evaluation_repository.get_test_run(session, test_run_id)
        if not test_run or test_run.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Test run not found',
            )

    if test_case_id:
        test_case = await evaluation_repository.get_test_case(
            session, test_case_id
        )
        if not test_case or test_case.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Test case not found',
            )

    if metric_id:
        metric = await evaluation_repository.get_metric(session, metric_id)
        if not metric or metric.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Metric not found',
            )

    if model_id:
        ai_model = await evaluation_repository.get_ai_model(session, model_id)
        if not ai_model or ai_model.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='AI model not found',
            )

    test_results = await evaluation_repository.get_test_results(
        session,
        test_run_id=test_run_id,
        test_case_id=test_case_id,
        metric_id=metric_id,
        model_id=model_id,
        offset=filters.offset,
        limit=filters.limit,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
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

