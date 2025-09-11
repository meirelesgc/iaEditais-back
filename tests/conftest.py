from contextlib import contextmanager
from datetime import datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from iaEditais.app import app
from iaEditais.database import get_session
from iaEditais.models import table_registry
from iaEditais.security import get_password_hash
from tests.factories import (
    BranchFactory,
    DocFactory,
    SourceFactory,
    TaxonomyFactory,
    TypificationFactory,
    UnitFactory,
    UserFactory,
)


@pytest.fixture
def client(session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def engine():
    with PostgresContainer('postgres:16', driver='psycopg') as postgres:
        _engine = create_async_engine(postgres.get_connection_url())
        yield _engine


@pytest_asyncio.fixture
async def session(engine):
    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.create_all)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(table_registry.metadata.drop_all)


@contextmanager
def _mock_db_time(*, model, time=datetime(2024, 1, 1)):
    def fake_insert_time_hook(mapper, connection, target):
        if hasattr(target, 'created_at'):
            target.created_at = time
        if hasattr(target, 'updated_at'):
            target.updated_at = time

    def fake_update_time_hook(mapper, connection, target):
        if hasattr(target, 'updated_at'):
            target.updated_at = time

    def fake_delete_time_hook(mapper, connection, target):
        if hasattr(target, 'deleted_at'):
            target.deleted_at = time

    event.listen(model, 'before_insert', fake_insert_time_hook)
    event.listen(model, 'before_update', fake_update_time_hook)
    event.listen(model, 'before_update', fake_delete_time_hook)

    yield time

    event.remove(model, 'before_insert', fake_insert_time_hook)
    event.remove(model, 'before_update', fake_update_time_hook)


@pytest.fixture
def mock_db_time():
    return _mock_db_time


@pytest_asyncio.fixture
def create_unit(session):
    async def _create_unit(**kwargs):
        unit = UnitFactory.build(**kwargs)
        session.add(unit)
        await session.commit()
        await session.refresh(unit)
        return unit

    return _create_unit


@pytest_asyncio.fixture
def create_user(session):
    async def _create_user(**kwargs):
        kwargs['password'] = get_password_hash(
            kwargs.get('password', 'defaultpass')
        )
        user = UserFactory.build(**kwargs)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    return _create_user


@pytest_asyncio.fixture
def create_source(session):
    async def _create_source(**kwargs):
        source = SourceFactory.build(**kwargs)
        session.add(source)
        await session.commit()
        await session.refresh(source)
        return source

    return _create_source


@pytest_asyncio.fixture
def create_typification(session):
    async def _create_source(**kwargs):
        source = TypificationFactory.build(**kwargs)
        session.add(source)
        await session.commit()
        await session.refresh(source, attribute_names=['sources'])
        return source

    return _create_source


@pytest_asyncio.fixture
def create_taxonomy(session):
    async def _create_taxonomy(**kwargs):
        taxonomy = TaxonomyFactory.build(**kwargs)
        session.add(taxonomy)
        await session.commit()
        await session.refresh(taxonomy)
        return taxonomy

    return _create_taxonomy


@pytest_asyncio.fixture
def create_branch(session):
    async def _create_branch(**kwargs):
        branch = BranchFactory.build(**kwargs)
        session.add(branch)
        await session.commit()
        await session.refresh(branch)
        return branch

    return _create_branch


@pytest_asyncio.fixture
def create_doc(session):
    async def _create_doc(**kwargs):
        doc = DocFactory.build(**kwargs)
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        return doc

    return _create_doc
