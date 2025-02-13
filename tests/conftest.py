import pytest

import os
from uuid import uuid4
from fpdf import FPDF
from iaEditais.config import Settings
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from iaEditais import app
from iaEditais.repositories import conn
from iaEditais.schemas.Typification import Typification


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


@pytest.fixture
def release_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(40, 10, 'Test Release')

    path = f'/tmp/release/{uuid4()}.pdf'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pdf.output(path)
    yield path
    os.remove(path)


@pytest.fixture
def typification():
    params = Typification(name='Test Typification')
    SCRIPT_SQL = """
        INSERT INTO typifications (id, name, created_at) 
        VALUES (%(id)s, %(name)s, %(created_at)s);
        """
    conn().exec(SCRIPT_SQL, params.model_dump())
    return params
