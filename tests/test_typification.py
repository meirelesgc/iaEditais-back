from iaEditais.schemas.typification import Typification

from http import HTTPStatus


def test_create_typification(client, create_typification):
    response = create_typification()
    assert response.status_code == HTTPStatus.CREATED
    typification = response.json()
    assert isinstance(Typification(**typification), Typification)
    assert len(typification['source']) > 0


def test_get_typification_empty(client):
    response = client.get('/typification/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_typification(client, typification):
    response = client.get('/typification/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_detailed_typification(client, typification):
    response = client.get(f'/typification/{typification.id}/')
    assert response.status_code == HTTPStatus.OK
    assert isinstance(Typification(**response.json()), Typification)


def test_put_typification(client, typification, create_source):
    new_source_id = create_source('New Source').json().get('id')
    updated_data = {
        'id': str(typification.id),
        'name': 'Updated Name',
        'created_at': typification.created_at.isoformat(),
        'source': [new_source_id],
    }
    response = client.put('/typification/', json=updated_data)
    assert response.status_code == HTTPStatus.OK

    response = client.get(f'/typification/{typification.id}/')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == 'Updated Name'
    assert new_source_id in response.json()['source']


def test_delete_typification(client, typification):
    response = client.delete(f'/typification/{typification.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/typification/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 0
