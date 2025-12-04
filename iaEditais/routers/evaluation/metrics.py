"""
Rotas CRUD para Metric e AIModel.
"""

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import AIModel, Metric
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    AIModelCreate,
    AIModelList,
    AIModelPublic,
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
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    """Lista todas as métricas ativas."""
    metrics = await evaluation_repository.get_metrics(
        session, filters.offset, filters.limit
    )
    return {'metrics': metrics}


@router.get('/{metric_id}', response_model=MetricPublic)
async def read_metric(metric_id: UUID, session: Session):
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


# ===========================
# AI Models Routes
# ===========================


@router.post(
    '/ai-models',
    status_code=HTTPStatus.CREATED,
    response_model=AIModelPublic,
)
async def create_ai_model(
    ai_model: AIModelCreate,
    session: Session,
    current_user: CurrentUser,
):
    """Cria um novo modelo de IA."""
    existing_model = await session.scalar(
        select(AIModel).where(
            AIModel.deleted_at.is_(None),
            AIModel.code_name == ai_model.code_name,
        )
    )

    if existing_model:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='AI Model code_name already exists',
        )

    db_model = await evaluation_repository.create_ai_model(
        session, ai_model.model_dump(), current_user
    )

    return db_model


@router.get('/ai-models', response_model=AIModelList)
async def read_ai_models(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    """Lista todos os modelos de IA ativos."""
    ai_models = await evaluation_repository.get_ai_models(
        session, filters.offset, filters.limit
    )
    return {'ai_models': ai_models}


@router.get('/ai-models/{model_id}', response_model=AIModelPublic)
async def read_ai_model(model_id: UUID, session: Session):
    """Busca um modelo de IA por ID."""
    ai_model = await evaluation_repository.get_ai_model(session, model_id)

    if not ai_model or ai_model.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='AI Model not found',
        )

    return ai_model

