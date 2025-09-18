from contextlib import contextmanager
from datetime import datetime

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from langchain_community.embeddings import FakeEmbeddings
from langchain_postgres import PGVector
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer

from iaEditais.app import app
from iaEditais.core.database import get_session
from iaEditais.core.vectorstore import get_vectorstore
from iaEditais.models import (
    DocumentHistory,
    DocumentStatus,
    Taxonomy,
    Typification,
    table_registry,
)
from iaEditais.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    create_access_token,
    get_password_hash,
)
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
def client(session, engine):
    async def get_vectorstore_override():
        vectorstore = PGVector(
            embeddings=FakeEmbeddings(size=256),
            connection=str(engine.url),
            use_jsonb=True,
            async_mode=True,
        )
        yield vectorstore

    def get_session_override():
        return session

    with TestClient(app) as client:
        app.dependency_overrides[get_session] = get_session_override
        app.dependency_overrides[get_vectorstore] = get_vectorstore_override
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def engine():
    with PostgresContainer('pgvector/pgvector:pg17', driver='psycopg') as p:
        _engine = create_async_engine(p.get_connection_url())
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
def logged_client(client, create_user, create_unit):
    async def _login(
        email: str = 'user@example.com',
        password: str = 'secret',
        **user_kwargs,
    ):
        unit = await create_unit()
        user = await create_user(
            email=email, password=password, unit_id=str(unit.id), **user_kwargs
        )
        token = create_access_token({'sub': user.email})
        client.cookies.set(ACCESS_TOKEN_COOKIE_NAME, token, path='/')
        auth_headers = {'Authorization': f'Bearer {token}'}
        return client, token, auth_headers, user

    return _login


@pytest_asyncio.fixture
def create_source(session):
    async def _create_source(**kwargs):
        source = SourceFactory.build(**kwargs)
        session.add(source)
        await session.commit()
        await session.refresh(
            source,
            attribute_names=['typifications'],
        )
        return source

    return _create_source


@pytest_asyncio.fixture
def create_typification(session):
    async def _create_typification(**kwargs):
        typification = TypificationFactory.build(**kwargs)
        session.add(typification)
        await session.commit()
        await session.refresh(
            typification, attribute_names=['sources', 'taxonomies']
        )
        return typification

    return _create_typification


@pytest_asyncio.fixture
def create_taxonomy(session):
    async def _create_taxonomy(**kwargs):
        taxonomy = TaxonomyFactory.build(**kwargs)
        session.add(taxonomy)
        await session.commit()
        await session.refresh(taxonomy, attribute_names=['typification'])
        typ = await session.get(Typification, taxonomy.typification_id)
        await session.refresh(typ, attribute_names=['taxonomies'])
        return taxonomy

    return _create_taxonomy


@pytest_asyncio.fixture
def create_branch(session):
    async def _create_branch(**kwargs):
        branch = BranchFactory.build(**kwargs)
        session.add(branch)
        await session.commit()
        await session.refresh(branch, attribute_names=['taxonomy'])
        tax = await session.get(Taxonomy, branch.taxonomy_id)
        await session.refresh(tax, attribute_names=['branches'])
        return branch

    return _create_branch


@pytest_asyncio.fixture
def create_doc(session):
    async def _create_doc(typification_ids: list[int] | None = None, **kwargs):
        doc = DocFactory.build(**kwargs)
        session.add(doc)
        await session.flush()

        history = DocumentHistory(
            document_id=doc.id,
            status=DocumentStatus.PENDING.value,
        )
        session.add(history)

        if typification_ids:
            typifications = await session.scalars(
                select(Typification).where(
                    Typification.id.in_(typification_ids)
                )
            )
            doc.typifications = [typ for typ in typifications.all()]

        await session.commit()
        await session.refresh(
            doc, attribute_names=['history', 'typifications']
        )
        return doc

    return _create_doc
