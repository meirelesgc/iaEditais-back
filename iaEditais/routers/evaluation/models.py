"""
Rotas CRUD para AIModel.
"""

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import AIModel
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    AIModelCreate,
    AIModelList,
    AIModelPublic,
    FilterPage,
)

router = APIRouter(
    prefix='/models',
    tags=['avaliação, modelos de IA'],
)


@router.post(
    '/',
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


@router.get('/', response_model=AIModelList)
async def read_ai_models(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    """Lista todos os modelos de IA ativos."""
    ai_models = await evaluation_repository.get_ai_models(
        session, filters.offset, filters.limit
    )
    return {'ai_models': ai_models}


@router.get('/{model_id}', response_model=AIModelPublic)
async def read_ai_model(model_id: UUID, session: Session):
    """Busca um modelo de IA por ID."""
    ai_model = await evaluation_repository.get_ai_model(session, model_id)

    if not ai_model or ai_model.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='AI Model not found',
        )

    return ai_model

