from iaEditais.schemas.Typification import Typification

from http import HTTPStatus


def test_create_typification(client):
    typification = {'name': 'Test type'}
    response = client.post('/typification/', json=typification)
    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Typification(**response.json()), Typification)


def test_get_typification_empty(client):
    response = client.get('/typification/')

    typifications = response.json()

    assert response.status_code == HTTPStatus.OK
    assert len(typifications) == 0


def test_get_typification(client, typification):
    response = client.get('/typification/')

    typifications = response.json()

    assert response.status_code == HTTPStatus.OK
    assert len(typifications) == 1


def test_get_detailed_typification(client, typification):
    response = client.get(f'/typification/{typification.id}/')

    assert response.status_code == HTTPStatus.OK
    assert isinstance(Typification(**response.json()), Typification)


def test_put_typification(client, typification):
    typification = {
        'id': str(typification.id),
        'name': 'Updated Name',
        'created_at': typification.created_at.isoformat(),
    }

    response = client.put('/typification/', json=typification)

    assert response.status_code == HTTPStatus.OK

    response = client.get(f'/typification/{typification["id"]}/')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == 'Updated Name'


def test_delete_typification(client, typification):
    response = client.delete(f'/typification/{typification.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/typification/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 0
