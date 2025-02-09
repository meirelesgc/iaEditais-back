import pytest
from iaEditais.config import Settings
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from iaEditais import app
from iaEditais.repositories import conn


@pytest.fixture
def client():
    return TestClient(app)


postgres = PostgresContainer('ankane/pgvector')


@pytest.fixture(scope='session', autouse=True)
def setup(request):
    postgres.start()

    def remove_container():
        postgres.stop()

    def connection_string(self):
        return f'postgresql://{postgres.username}:{postgres.password}@{postgres.get_container_host_ip()}:{postgres.get_exposed_port(5432)}/{postgres.dbname}'

    request.addfinalizer(remove_container)
    Settings.get_connection_string = connection_string


@pytest.fixture(scope='function', autouse=True)
def setup_data():
    SCRIPT_SQL = """
        DROP SCHEMA IF EXISTS public CASCADE;
        CREATE SCHEMA public;
        """
    conn().exec(SCRIPT_SQL)

    with open('init.sql', 'r') as buffer:
        conn().exec(buffer.read())


@pytest.fixture
def taxonomy_payload():
    return {
        'title': 'Test Taxonomy',
        'description': 'This is a test taxonomy.',
        'source': [],
    }


@pytest.fixture
def branch_payload():
    return {
        'title': 'Test Branch',
        'description': 'Test description',
    }
