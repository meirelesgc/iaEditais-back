import json
from pathlib import Path
from typing import override

import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from langchain_community.embeddings import FakeEmbeddings
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_postgres import PGVector
from starlette.datastructures import UploadFile as StarletteUploadFile
from testcontainers.postgres import PostgresContainer

from iaEditais.app import app
from iaEditais.core.cache import get_cache
from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn
from iaEditais.core.model import get_model
from iaEditais.core.vectorstore import get_vectorstore
from iaEditais.models import doc as doc_model
from iaEditais.services import (
    doc_service,
    source_service,
    taxonomy_service,
    typification_service,
    unit_service,
    user_service,
)
from iaEditais.services import taxonomy_service as taxonomy_services
from tests.factories import (
    branch_factory,
    doc_factory,
    source_factory,
    taxonomy_factory,
    typification_factory,
    unit_factory,
    user_factory,
)


@pytest.fixture(scope='session', autouse=True)
def postgres():
    with PostgresContainer('pgvector/pgvector:pg17') as pg:
        yield pg


async def reset_database(conn: Connection):
    SCRIPT_SQL = 'DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;'
    await conn.exec(SCRIPT_SQL)
    with open('init.sql', 'r', encoding='utf-8') as buffer:
        await conn.exec(buffer.read())


@pytest_asyncio.fixture
async def conn(postgres):
    connection_url = f'postgresql://{postgres.username}:{postgres.password}@{postgres.get_container_host_ip()}:{postgres.get_exposed_port(5432)}/{postgres.dbname}'
    conn = Connection(connection_url, max_size=20, timeout=10)
    await conn.connect()
    await reset_database(conn)
    yield conn
    await conn.disconnect()


@pytest_asyncio.fixture
async def model():
    class FakeModel(FakeChatModel):
        @override
        def _call(self, messages, stop=None, run_manager=None, **kwargs) -> str:
            return json.dumps({})

    return FakeModel()


@pytest_asyncio.fixture
async def vectorstore(postgres):
    connection_url = f'postgresql+psycopg://{postgres.username}:{postgres.password}@{postgres.get_container_host_ip()}:{postgres.get_exposed_port(5432)}/{postgres.dbname}'
    vectorstore = PGVector(
        embeddings=FakeEmbeddings(size=256),
        connection=connection_url,
        use_jsonb=True,
        async_mode=True,
    )

    yield vectorstore


@pytest_asyncio.fixture
async def cache():
    fake_redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake_redis_client
    await fake_redis_client.close()


@pytest.fixture
def client(conn, model, vectorstore, cache):
    async def get_conn_override():
        yield conn

    async def get_vectorstore_override():
        yield vectorstore

    async def get_model_override():
        yield model

    async def get_cache_override():
        yield cache

    app.dependency_overrides[get_conn] = get_conn_override
    app.dependency_overrides[get_model] = get_model_override
    app.dependency_overrides[get_vectorstore] = get_vectorstore_override
    app.dependency_overrides[get_cache] = get_cache_override

    return TestClient(app)


@pytest.fixture
def create_source(conn):
    async def _create_source(**kwargs):
        source = source_factory.CreateSourceFactory(**kwargs)
        source = await source_service.source_post(conn, source)
        return source

    return _create_source


@pytest.fixture
def create_source_with_upload(conn):
    async def _create_source_with_upload(**kwargs):
        source = source_factory.CreateSourceFactory(**kwargs)
        source = await source_service.source_post(conn, source)

        path = Path('tests/storage/sample.pdf')
        with path.open('rb') as f:
            upload_file = StarletteUploadFile(filename='sample.pdf', file=f)
            await source_service.source_upload_post(conn, source.id, upload_file)

        return source

    return _create_source_with_upload


@pytest.fixture
def create_typification(conn):
    async def _create_typification(**kwargs):
        typification = typification_factory.CreateTypificationFactory(**kwargs)
        typification = await typification_service.type_post(conn, typification)
        return typification

    return _create_typification


@pytest.fixture
def create_taxonomy(conn):
    async def _create_taxonomy(typification, **kwargs):
        kwargs['typification_id'] = typification.id
        taxonomy = taxonomy_factory.CreateTaxonomyFactory(**kwargs)
        taxonomy = await taxonomy_service.post_taxonomy(conn, taxonomy)
        return taxonomy

    return _create_taxonomy


@pytest.fixture
def create_branch(conn):
    async def _create_branch(taxonomy, **kwargs):
        kwargs['taxonomy_id'] = taxonomy.id
        branch = branch_factory.CreateBranchFactory(**kwargs)
        branch = await taxonomy_services.post_branch(conn, branch)
        return branch

    return _create_branch


@pytest.fixture
def create_user(conn):
    async def _create_user(**kwargs):
        raw_user = user_factory.CreateUserFactory(**kwargs)
        password = raw_user.password
        created_user = await user_service.post_user(
            conn, raw_user, access_level='DEFAULT'
        )
        created_user.password = password
        return created_user

    return _create_user


@pytest.fixture
def create_admin_user(conn):
    async def _create_admin_user(**kwargs):
        raw_user = user_factory.CreateUserFactory(**kwargs)
        password = raw_user.password
        created_user = await user_service.post_user(
            conn, raw_user, access_level='ADMIN'
        )
        created_user.password = password
        return created_user

    return _create_admin_user


@pytest.fixture
def get_token(client):
    def _get_token(user):
        data = {'username': user.email, 'password': user.password}
        response = client.post('/token/', data=data)
        return response.json()['access_token']

    return _get_token


@pytest.fixture
def auth_header(get_token):
    def _auth_header(user):
        return {'Authorization': f'Bearer {get_token(user)}'}

    return _auth_header


@pytest.fixture
def create_unit(conn):
    async def _create_unit():
        unit = unit_factory.CreateUnitFactory()
        unit = await unit_service.unit_post(conn, unit)
        return unit

    return _create_unit


@pytest.fixture
def create_doc(conn, create_typification):
    async def _create_doc():
        typification = await create_typification()
        doc_data = doc_factory.CreateDocFactory(typification=[typification.id])
        doc = await doc_service.doc_post(conn, doc_data)
        return doc

    return _create_doc


@pytest.fixture
def create_release(client):
    async def _create_release(doc: doc_model.Doc):
        doc_id = str(doc.id)
        path = 'tests/storage/sample.pdf'
        with open(path, 'rb') as f:
            files = {'file': (path, f, 'application/pdf')}
            response = client.post(f'/doc/{doc_id}/release/', files=files)
        return doc_model.Release(**response.json())

    return _create_release
