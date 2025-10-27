from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import TestCaseMetric
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    TestCaseMetricCreate,
    TestCaseMetricList,
    TestCaseMetricPublic,
)

router = APIRouter(
    prefix='/test-case-metrics',
    tags=['avaliação, associação caso-métrica'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TestCaseMetricPublic,
)
async def create_test_case_metric(
    test_case_metric: TestCaseMetricCreate,
    session: Session,
    current_user: CurrentUser,
):
    """Cria uma nova associação entre caso de teste e métrica."""
    # Valida se o caso de teste existe
    test_case = await evaluation_repository.get_test_case(session, test_case_metric.test_case_id)
    if not test_case or test_case.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test case not found',
        )

    # Valida se a métrica existe
    metric = await evaluation_repository.get_metric(session, test_case_metric.metric_id)
    if not metric or metric.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Metric not found',
        )

    # Verifica se já existe a associação
    existing_association = await session.scalar(
        select(TestCaseMetric).where(
            TestCaseMetric.deleted_at.is_(None),
            TestCaseMetric.test_case_id == test_case_metric.test_case_id,
            TestCaseMetric.metric_id == test_case_metric.metric_id,
        )
    )

    if existing_association:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Association between test case and metric already exists',
        )

    db_test_case_metric = await evaluation_repository.create_test_case_metric(
        session, test_case_metric.model_dump(), current_user
    )

    return db_test_case_metric


@router.get('/', response_model=TestCaseMetricList)
async def read_test_case_metrics(
    session: Session, 
    filters: Annotated[FilterPage, Depends()],
    test_case_id: Optional[UUID] = None,
):
    """Lista todas as associações caso-métrica ativas."""
    test_case_metrics = await evaluation_repository.get_test_case_metrics(
        session, test_case_id, filters.offset, filters.limit
    )
    return {'test_case_metrics': test_case_metrics}


@router.get('/{test_case_metric_id}', response_model=TestCaseMetricPublic)
async def read_test_case_metric(test_case_metric_id: UUID, session: Session):
    """Busca uma associação caso-métrica por ID."""
    test_case_metric = await evaluation_repository.get_test_case_metric(session, test_case_metric_id)

    if not test_case_metric or test_case_metric.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test case metric association not found',
        )

    return test_case_metric
