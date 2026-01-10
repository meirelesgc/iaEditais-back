"""
Rotas CRUD para Metric.
"""

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Metric
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    MetricCreate,
    MetricList,
    MetricPublic,
    MetricUpdate,
)

router = APIRouter(
    prefix='/metrics',
    tags=['avaliação, métricas'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=MetricPublic,
)
async def create_metric(
    metric: MetricCreate,
    session: Session,
    current_user: CurrentUser,
):
    """Cria uma nova métrica."""
    existing_metric = await session.scalar(
        select(Metric).where(
            Metric.deleted_at.is_(None),
            Metric.name == metric.name,
        )
    )

    if existing_metric:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Metric name already exists',
        )

    db_metric = await evaluation_repository.create_metric(
        session, metric.model_dump(), current_user
    )

    return db_metric


@router.get('/', response_model=MetricList)
async def read_metrics(
    session: Session,
    current_user: CurrentUser,
    filters: Annotated[FilterPage, Depends()],
):
    """Lista todas as métricas ativas."""
    metrics = await evaluation_repository.get_metrics(
        session, filters.offset, filters.limit
    )
    return {'metrics': metrics}


@router.get('/{metric_id}', response_model=MetricPublic)
async def read_metric(metric_id: UUID, session: Session, current_user: CurrentUser):
    """Busca uma métrica por ID."""
    metric = await evaluation_repository.get_metric(session, metric_id)

    if not metric or metric.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Metric not found',
        )

    return metric


@router.put('/{metric_id}', response_model=MetricPublic)
async def update_metric(
    metric_id: UUID,
    metric_data: MetricUpdate,
    session: Session,
    current_user: CurrentUser,
):
    """Atualiza uma métrica."""
    updated_metric = await evaluation_repository.update_metric(
        session, metric_id, metric_data.model_dump(), current_user
    )

    if not updated_metric:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Metric not found'
        )

    return updated_metric


@router.delete('/{metric_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_metric(
    metric_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Remove (soft delete) uma métrica."""
    deleted_metric = await evaluation_repository.delete_metric(
        session, metric_id, current_user
    )

    if not deleted_metric:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Metric not found'
        )
