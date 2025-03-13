from http import HTTPStatus
from iaEditais.schemas.Order import Order, Release


def test_create_order(client, typification):
    typification_id = str(typification.id)
    order = {'name': 'Test Order', 'typification': [typification_id]}
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
    response = client.delete(f'/order/{order.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/order/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_create_release(
    client, pdf, order, create_taxonomy, create_branch, mocker
):
    for typification_id in order.typification:
        response = create_taxonomy(typification_id=str(typification_id))
        create_branch(taxonomy_id=response.json()['id'])

    mocker.patch(
        'iaEditais.integrations.Integrations.analyze_release',
        side_effect=lambda release: release,
    )

    with open(pdf, 'rb') as buffer:
        file = {'file': ('testfile1.pdf', buffer, 'application/pdf')}
        response = client.post(f'/order/{order.id}/release/', files=file)

    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Release(**response.json()), Release)
