from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Test
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    TestCreate,
    TestList,
    TestPublic,
)

router = APIRouter(
    prefix='/tests',
    tags=['avaliação, testes'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TestPublic,
)
async def create_test(
    test: TestCreate,
    session: Session,
    current_user: CurrentUser,
):
    """Cria um novo teste."""
    # Verifica se já existe um teste com o mesmo nome
    existing_test = await session.scalar(
        select(Test).where(
            Test.deleted_at.is_(None),
            Test.name == test.name,
        )
    )

    if existing_test:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Test name already exists',
        )

    db_test = await evaluation_repository.create_test(
        session, test.model_dump(), current_user
    )

    return db_test


@router.get('/', response_model=TestList)
async def read_tests(
    session: Session, 
    filters: Annotated[FilterPage, Depends()]
):
    """Lista todos os testes ativos."""
    tests = await evaluation_repository.get_tests(
        session, filters.offset, filters.limit
    )
    return {'tests': tests}


@router.get('/{test_id}', response_model=TestPublic)
async def read_test(test_id: UUID, session: Session):
    """Busca um teste por ID."""
    test = await evaluation_repository.get_test(session, test_id)

    if not test or test.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test not found',
        )

    return test
