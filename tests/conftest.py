import io
import shutil
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import override
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from faststream.rabbit import TestRabbitBroker
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_postgres import PGVector
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import AsyncRedisContainer

from iaEditais import workers
from iaEditais.app import app
from iaEditais.core.broker import get_broker
from iaEditais.core.database import get_session
from iaEditais.core.llm import get_model
from iaEditais.core.security import (
    ACCESS_TOKEN_COOKIE_NAME,
    create_access_token,
    get_password_hash,
)
from iaEditais.core.vectorstore import get_vectorstore
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentRelease,
    DocumentStatus,
    Source,
    Taxonomy,
    Typification,
    table_registry,
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


@pytest_asyncio.fixture
async def client(
    session,
    engine,
    # cache,
):
    async def get_vstore_override():
        vectorstore = PGVector(
            embeddings=FakeEmbeddings(size=256),
            connection=engine.url.render_as_string(hide_password=False),
            use_jsonb=True,
            async_mode=True,
        )
        yield vectorstore

    async def get_model_override():
        class FakeModel(FakeChatModel):
            @override
            def _call(self, messages, stop=None, run_manager=None, **kwargs):
                return '{"feedback": "", "fulfilled": true, "score": "3"}'

        return FakeModel()

    def get_session_override():
        return session

    # def get_cache_override():
    #     yield cache.get_async_client()
    async with TestRabbitBroker(workers.router.broker) as broker:
        with TestClient(app) as client:
            app.dependency_overrides[get_session] = get_session_override
            app.dependency_overrides[get_vectorstore] = get_vstore_override
            app.dependency_overrides[get_model] = get_model_override
            app.dependency_overrides[get_broker] = lambda: broker
            # app.dependency_overrides[get_cache] = get_cache_override
            yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope='session')
def engine():
    with PostgresContainer('pgvector/pgvector:pg17', driver='psycopg') as p:
        _engine = create_async_engine(p.get_connection_url())
        yield _engine


@pytest.fixture(scope='session')
def cache():
    with AsyncRedisContainer('redis:latest') as redis:
        return redis


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
        await session.refresh(source)
        return source

    return _create_source


@pytest_asyncio.fixture
def create_typification(session):
    async def _create_typification(**kwargs):
        source_ids = kwargs.pop('source_ids', None)
        db_typification = TypificationFactory.build(**kwargs)

        if source_ids:
            sources = await session.scalars(
                select(Source).where(Source.id.in_(source_ids))
            )
            db_typification.sources = sources.all()

        session.add(db_typification)
        await session.commit()
        await session.refresh(db_typification)
        for source in db_typification.sources:
            await session.refresh(source)
        return db_typification

    return _create_typification


@pytest_asyncio.fixture
def create_taxonomy(session):
    async def _create_taxonomy(**kwargs):
        taxonomy = TaxonomyFactory.build(**kwargs)
        session.add(taxonomy)
        await session.commit()
        await session.refresh(taxonomy)
        typ = await session.get(Typification, taxonomy.typification_id)
        await session.refresh(typ)
        return taxonomy

    return _create_taxonomy


@pytest_asyncio.fixture
def create_branch(session):
    async def _create_branch(**kwargs):
        branch = BranchFactory.build(**kwargs)
        session.add(branch)
        await session.commit()
        await session.refresh(branch)
        tax = await session.get(Taxonomy, branch.taxonomy_id)
        await session.refresh(tax)
        return branch

    return _create_branch


@pytest_asyncio.fixture
def create_doc(session, create_unit):
    async def _create_doc(typification_ids: list[int] | None = None, **kwargs):
        unit = await create_unit()
        doc = DocFactory.build(**kwargs, unit_id=unit.id)
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
        await session.refresh(doc)
        return doc

    return _create_doc


@pytest_asyncio.fixture
def create_release(session):
    async def _create_release(doc: Document):
        if len(doc.typifications) == 0:
            raise Exception('There are no associated typifications')

        latest_history = doc.history[0]
        file_content = b'Este eh um arquivo de teste.'
        file = {'file': ('test_release.txt', io.BytesIO(file_content))}

        file_path = f'iaEditais/storage/temp/{uuid4()}.txt'
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file['file'][1], buffer)

        db_release = DocumentRelease(
            history_id=latest_history.id, file_path=file_path
        )

        session.add(db_release)
        await session.commit()
        await session.refresh(db_release)

        return db_release

    return _create_release


@pytest.fixture(autouse=True)
def mock_upload_directory(monkeypatch):
    temp_upload_dir = Path('iaEditais') / 'storage' / 'temp'
    temp_upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        'iaEditais.services.releases_service.UPLOAD_DIRECTORY',
        str(temp_upload_dir),
    )
    monkeypatch.setattr(
        'iaEditais.workers.docs.releases.UPLOAD_DIRECTORY',
        str(temp_upload_dir),
    )

    monkeypatch.setattr(
        'iaEditais.routers.check_tree.sources.UPLOAD_DIRECTORY',
        str(temp_upload_dir),
    )
    return str(temp_upload_dir)
