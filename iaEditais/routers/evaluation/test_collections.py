"""
Rotas CRUD para TestCollection.
"""

from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import TestCollection
from iaEditais.repositories import evaluation_repository
from iaEditais.schemas import (
    FilterPage,
    TestCollectionCreate,
    TestCollectionList,
    TestCollectionPublic,
    TestCollectionUpdate,
)

router = APIRouter(
    prefix='/test-collections',
    tags=['avaliação, coleções de testes'],
)


@router.post(
    '/',
    status_code=HTTPStatus.CREATED,
    response_model=TestCollectionPublic,
)
async def create_test_collection(
    test_collection: TestCollectionCreate,
    session: Session,
    current_user: CurrentUser,
):
    """Cria uma nova coleção de testes."""
    existing_collection = await session.scalar(
        select(TestCollection).where(
            TestCollection.deleted_at.is_(None),
            TestCollection.name == test_collection.name,
        )
    )

    if existing_collection:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Test collection name already exists',
        )

    db_test_collection = await evaluation_repository.create_test_collection(
        session, test_collection.model_dump(), current_user
    )

    return db_test_collection


@router.get('/', response_model=TestCollectionList)
async def read_test_collections(
    session: Session, filters: Annotated[FilterPage, Depends()]
):
    """Lista todas as coleções de testes ativas."""
    test_collections = await evaluation_repository.get_test_collections(
        session, filters.offset, filters.limit
    )
    return {'test_collections': test_collections}


@router.get('/{collection_id}', response_model=TestCollectionPublic)
async def read_test_collection(collection_id: UUID, session: Session):
    """Busca uma coleção de testes por ID."""
    test_collection = await evaluation_repository.get_test_collection(
        session, collection_id
    )

    if not test_collection or test_collection.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Test collection not found',
        )

    return test_collection


@router.put('/{collection_id}', response_model=TestCollectionPublic)
async def update_test_collection(
    collection_id: UUID,
    test_collection_data: TestCollectionUpdate,
    session: Session,
    current_user: CurrentUser,
):
    """Atualiza uma coleção de testes."""
    updated_collection = await evaluation_repository.update_test_collection(
        session, collection_id, test_collection_data.model_dump(), current_user
    )

    if not updated_collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Test collection not found'
        )

    return updated_collection


@router.delete('/{collection_id}', status_code=HTTPStatus.NO_CONTENT)
async def delete_test_collection(
    collection_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    """Remove (soft delete) uma coleção de testes."""
    deleted_collection = await evaluation_repository.delete_test_collection(
        session, collection_id, current_user
    )

    if not deleted_collection:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail='Test collection not found'
        )

