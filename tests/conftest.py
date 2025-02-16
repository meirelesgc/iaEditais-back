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
from iaEditais.schemas.Taxonomy import Taxonomy
from iaEditais.schemas.Branch import Branch
from iaEditais.schemas.Order import Order


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
def source_data_factory():
    def _factory(
        name='Test Source',
        file_content=b'%PDF-1.4\n...fake pdf content...',
        description='Test Description',
    ):
        return {
            'data': {'name': name, 'description': description},
            'files': {
                'file': ('testfile.pdf', file_content, 'application/pdf')
            },
        }

    return _factory


@pytest.fixture
def create_source(client, source_data_factory):
    def _create(
        name='Test Source',
        file_content=b'%PDF-1.4\n...fake pdf content...',
        description='Test Description',
    ):
        source_data = source_data_factory(name, file_content, description)
        return client.post(
            '/source/',
            files=source_data['files'],
            data=source_data['data'],
        )

    return _create


@pytest.fixture
def typification_data_factory():
    def _factory(name='Test type', source_ids=None):
        return {'name': name, 'source': source_ids or []}

    return _factory


@pytest.fixture
def create_typification(client, typification_data_factory, create_source):
    def _create(name='Test type', source_count=1):
        source_ids = [
            create_source(f'Test Source {uuid4()}').json().get('id')
            for _ in range(source_count)
        ]
        data = typification_data_factory(name, source_ids)
        return client.post('/typification/', json=data)

    return _create


@pytest.fixture
def typification(client, create_typification):
    response = create_typification()
    return Typification(**response.json())


@pytest.fixture
def taxonomy_data_factory():
    def _factory(
        typification_id=None,
        title='Test Taxonomy',
        description='Test Description',
        source_ids=None,
    ):
        return {
            'typification_id': typification_id or None,
            'title': title,
            'description': description,
            'source': source_ids or [],
        }

    return _factory


@pytest.fixture
def create_taxonomy(
    client,
    taxonomy_data_factory,
    create_source,
    create_typification,
):
    def _create(
        title='Test Taxonomy',
        description='Test Description',
        source_count=1,
    ):
        typification_id = create_typification().json().get('id')
        source_ids = [
            create_source(f'Test Source {uuid4()}').json().get('id')
            for _ in range(source_count)
        ]
        data = taxonomy_data_factory(
            typification_id,
            title,
            description,
            source_ids,
        )
        response = client.post('/taxonomy/', json=data)
        return response

    return _create


@pytest.fixture
def taxonomy(client, create_taxonomy):
    response = create_taxonomy()
    return Taxonomy(**response.json())


@pytest.fixture
def branch_data_factory():
    def _factory(
        taxonomy_id=None,
        title='Test Branch',
        description='Test Description',
    ):
        return {
            'taxonomy_id': taxonomy_id or None,
            'title': title,
            'description': description,
        }

    return _factory


@pytest.fixture
def create_branch(client, create_taxonomy, branch_data_factory):
    def _create(
        taxonomy_id=None,
        title='Test Branch',
        description='Test Description',
    ):
        taxonomy_id = create_taxonomy().json()['id']
        data = branch_data_factory(
            taxonomy_id,
            title,
            description,
        )
        response = client.post('/taxonomy/branch/', json=data)
        return response

    return _create


@pytest.fixture
def branch(client, create_branch):
    response = create_branch()
    return Branch(**response.json())


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
def order_data_factory():
    def _factory(name='Test Order', typifications=[]):
        return {
            'name': name,
            'typifications': typifications or [],
        }

    return _factory


@pytest.fixture
def create_order(client, create_typification):
    def _create(
        name='Test Order',
        typification_count=1,
    ):
        typifications = [
            create_typification(f'Test Typification {uuid4()}')
            .json()
            .get('id')
            for _ in range(typification_count)
        ]
        data = {'name': name, 'typification': typifications}
        return client.post('/order/', json=data)

    return _create


@pytest.fixture
def order(client, create_order):
    response = create_order()
    return Order(**response.json())
