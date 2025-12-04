"""
Rotas CRUD para TestCase.
"""

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
    TestCaseUpdate,
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
    # Valida se a coleção de teste existe
    test_collection = await evaluation_repository.get_test_collection(
        session, test_case.test_collection_id
    )
    if not test_collection or test_collection.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test collection not found',
        )

    # Valida se a branch existe (se fornecida)
    if test_case.branch_id:
        branch = await evaluation_repository.get_branch_by_name_or_id(
            session, test_case.branch_id
        )
        if not branch:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Branch not found',
            )

    # Verifica unicidade do nome dentro da coleção
    existing_test_case = await session.scalar(
        select(TestCase).where(
            TestCase.deleted_at.is_(None),
            TestCase.name == test_case.name,
            TestCase.test_collection_id == test_case.test_collection_id,
            TestCase.doc_id == test_case.doc_id,
        )
    )

    if existing_test_case:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Test case name already exists for this collection and document',
        )

    db_test_case = await evaluation_repository.create_test_case(
        session, test_case.model_dump(), current_user
    )

    return db_test_case


@router.get('/', response_model=TestCaseList)
async def read_test_cases(
    session: Session,
    filters: Annotated[FilterPage, Depends()],
    test_collection_id: Optional[UUID] = None,
):
    """Lista todos os casos de teste ativos."""
    test_cases = await evaluation_repository.get_test_cases(
        session, test_collection_id, filters.offset, filters.limit
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


@router.put('/{test_case_id}', response_model=TestCasePublic)
async def update_test_case(
    test_case_id: UUID,
    test_case_data: TestCaseUpdate,
    session: Session,
    current_user: CurrentUser,
):
    """Atualiza um caso de teste."""
    # Se o nome for alterado, verifica se já existe
    if test_case_data.name:
        db_test_case = await evaluation_repository.get_test_case(
            session, test_case_id
        )
        if not db_test_case:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail='Test case not found',
            )

        existing_test_case = await session.scalar(
            select(TestCase).where(
                TestCase.deleted_at.is_(None),
                TestCase.name == test_case_data.name,
                TestCase.test_collection_id == db_test_case.test_collection_id,
                TestCase.doc_id == db_test_case.doc_id,
                TestCase.id != test_case_id,
            )
        )
        if existing_test_case:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Test case name already exists for this collection and document',
            )

    updated_test_case = await evaluation_repository.update_test_case(
        session,
        test_case_id,
        test_case_data.model_dump(exclude_unset=True),
        current_user,
    )

    if not updated_test_case:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test case not found',
        )

    return updated_test_case


@router.delete('/{test_case_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_test_case(
    test_case_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Remove um caso de teste."""
    deleted_test_case = await evaluation_repository.delete_test_case(
        session, test_case_id, current_user
    )

    if not deleted_test_case:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test case not found',
        )

