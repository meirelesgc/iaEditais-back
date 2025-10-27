from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import TestCase
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    TestCaseCreate,
    TestCaseList,
    TestCasePublic,
)

router = APIRouter(
    prefix='/test-cases',
    tags=['avaliação, casos de teste'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TestCasePublic,
)
async def create_test_case(
    test_case: TestCaseCreate,
    session: Session,
    current_user: CurrentUser,
):
    """Cria um novo caso de teste."""
    # Valida se o teste existe
    test = await evaluation_repository.get_test(session, test_case.test_id)
    if not test or test.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test not found',
        )

    # Valida se a branch existe (se fornecida)
    if test_case.branch_id or test_case.branch_name:
        branch = await evaluation_repository.get_branch_by_name_or_id(
            session, test_case.branch_id, test_case.branch_name
        )
        if not branch:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Branch not found',
            )

    # Verifica unicidade do nome dentro do teste
    existing_test_case = await session.scalar(
        select(TestCase).where(
            TestCase.deleted_at.is_(None),
            TestCase.name == test_case.name,
            TestCase.test_id == test_case.test_id,
            TestCase.doc_id == test_case.doc_id,
        )
    )

    if existing_test_case:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Test case name already exists for this test and document',
        )

    db_test_case = await evaluation_repository.create_test_case(
        session, test_case.model_dump(), current_user
    )

    return db_test_case


@router.get('/', response_model=TestCaseList)
async def read_test_cases(
    session: Session, 
    filters: Annotated[FilterPage, Depends()],
    test_id: Optional[UUID] = None,
):
    """Lista todos os casos de teste ativos."""
    test_cases = await evaluation_repository.get_test_cases(
        session, test_id, filters.offset, filters.limit
    )
    return {'test_cases': test_cases}


@router.get('/{test_case_id}', response_model=TestCasePublic)
async def read_test_case(test_case_id: UUID, session: Session):
    """Busca um caso de teste por ID."""
    test_case = await evaluation_repository.get_test_case(session, test_case_id)

    if not test_case or test_case.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test case not found',
        )

    return test_case
