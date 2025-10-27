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
    # Verifica se já existe uma métrica com o mesmo nome para o mesmo modelo
    existing_metric = await session.scalar(
        select(Metric).where(
            Metric.deleted_at.is_(None),
            Metric.name == metric.name,
            Metric.model_id == metric.model_id,
        )
    )

    if existing_metric:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Metric name already exists for this model',
        )

    # Valida se o modelo existe (se fornecido)
    if metric.model_id:
        model = await evaluation_repository.get_ai_model(session, metric.model_id)
        if not model or model.deleted_at:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='AI Model not found',
            )

    db_metric = await evaluation_repository.create_metric(
        session, metric.model_dump(), current_user
    )

    return db_metric


@router.get('/', response_model=MetricList)
async def read_metrics(
    session: Session, 
    filters: Annotated[FilterPage, Depends()]
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
    # Verifica se já existe um modelo com o mesmo code_name
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
    session: Session, 
    filters: Annotated[FilterPage, Depends()]
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
