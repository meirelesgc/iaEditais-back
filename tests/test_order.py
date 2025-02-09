from iaEditais.schemas.Order import Order, DetailedOrder

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


def test_create_release(client): ...


def test_create_release_with_taxonomies(client): ...
