import pytest

from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from iaEditais import app


@pytest.fixture
def client():
    return TestClient(app)


postgres = PostgresContainer('ankane/pgvector')


@pytest.fixture(scope='module', autouse=True)
def setup(request):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)
