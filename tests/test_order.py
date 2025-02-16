import pytest
import os
from uuid import uuid4
from http import HTTPStatus
from fpdf import FPDF
from iaEditais.schemas.Order import Order, DetailedOrder, Release


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
def create_order(client):
    def _create(name='Test Order'):
        response = client.post('/order/', json={'name': name})
        assert response.status_code == HTTPStatus.CREATED
        return response.json()

    return _create


@pytest.fixture
def order(client, create_order):
    return create_order()


def test_create_order(client):
    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)
    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Order(**response.json()), Order)


def test_get_order_with_one_order(client, order):
    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_order_with_multiple_orders(client, create_order):
    create_order()
    create_order()

    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2


def test_delete_order(client, order):
    response = client.delete(f'/order/{order["id"]}')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_detailed_order(client, order):
    response = client.get(f'/order/{order["id"]}/')
    assert response.status_code == HTTPStatus.OK
    assert isinstance(DetailedOrder(**response.json()), DetailedOrder)


def test_create_release_no_taxonomies(client, order, release_pdf):
    data = {'order_id': order['id']}

    with open(release_pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post('/order/release/', data=data, files=file)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Invalid taxonomy structure.'}


def test_create_release_with_invalid_taxonomies(
    client, taxonomy, release_pdf, order
):
    taxonomy_id = str(taxonomy.id)

    data = {'order_id': order['id'], 'taxonomies': [taxonomy_id]}

    with open(release_pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post('/order/release/', data=data, files=file)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Invalid taxonomy structure.'}


def test_create_release(client, branch, release_pdf, mocker, order):
    taxonomy_id = str(branch.taxonomy_id)

    data = {'order_id': order['id'], 'taxonomies': [taxonomy_id]}

    mocker.patch(
        'iaEditais.integrations.OrderIntegrations.analyze_release',
        return_value=['Test Taxonomy 1'],
    )

    with open(release_pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post('/order/release/', data=data, files=file)

    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Release(**response.json()), Release)

    response = client.get(f'/order/{order["id"]}/')
    assert response.status_code == HTTPStatus.OK
    assert isinstance(DetailedOrder(**response.json()), DetailedOrder)
