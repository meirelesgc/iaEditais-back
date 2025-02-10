from iaEditais.schemas.Order import Order, DetailedOrder, Release

from http import HTTPStatus


def test_create_order(client):
    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)
    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Order(**response.json()), Order)


def test_get_order_with_one_order(client):
    order = {'name': 'Test Order'}
    client.post('/order/', json=order)

    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_order_with_multiple_records(client):
    order = {'name': 'Test Order'}
    for _ in range(2):
        client.post('/order/', json=order)

    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2


def test_delete_order(client):
    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)

    response = client.delete(f'/order/{response.json()["id"]}')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_detailed_order(client):
    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)

    response = client.get(f'/order/{response.json()["id"]}/')

    assert response.status_code == HTTPStatus.OK
    assert isinstance(DetailedOrder(**response.json()), DetailedOrder)


def test_create_release_no_taxonomies(client, release_pdf):
    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)
    order_id = response.json().get('id')

    order_id = str(order_id)

    data = {'order_id': order_id}

    with open(release_pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post('/order/release/', data=data, files=file)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Invalid taxonomy structure.'}


def test_create_release_with_invalide_taxonomies(
    client, taxonomy_payload, release_pdf
):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    taxonomy_id = str(response.json().get('id'))

    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)

    order_id = str(response.json().get('id'))

    data = {'order_id': order_id, 'taxonomies': [taxonomy_id]}

    with open(release_pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post('/order/release/', data=data, files=file)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json() == {'detail': 'Invalid taxonomy structure.'}


def test_create_release(
    client, taxonomy_payload, branch_payload, release_pdf, mocker
):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    taxonomy_id = str(response.json().get('id'))

    branch_payload['taxonomy_id'] = response.json()['id']
    response = client.post('/taxonomy/branch/', json=branch_payload)

    order = {'name': 'Test Order'}
    response = client.post('/order/', json=order)

    order_id = str(response.json().get('id'))

    data = {'order_id': order_id, 'taxonomies': [taxonomy_id]}

    mocker.patch(
        'iaEditais.integrations.OrderIntegrations.analyze_release',
        return_value=['Test Taxonomy 1'],
    )

    with open(release_pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post('/order/release/', data=data, files=file)

    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Release(**response.json()), Release)
