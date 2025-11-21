from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from iaEditais.app import app
from iaEditais.core.connection import Connection
from iaEditais.core.database import get_conn


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


@pytest.fixture
def client(conn):
    async def get_conn_override():
        yield conn

    app.dependency_overrides[get_conn] = get_conn_override
    return TestClient(app)


@pytest.fixture
def create_source(client):
    async def _create_source(
        name='default_name',
        description='default_description',
        **kwargs,
    ):
        file_path = Path('storage/tests/source.pdf')
        data = {'name': name, 'description': description}
        with file_path.open('rb') as f:
            file = {'file': f}

            response = client.post('/source/', files=file, data=data)
        return response.json()

    return _create_source
