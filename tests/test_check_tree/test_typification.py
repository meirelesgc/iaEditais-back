import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import TypificationPublic


def test_create_typification(client):
    response = client.post(
        '/typification/',
        json={'name': 'Financial Reports'},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Financial Reports'
    assert data['sources'] == []


@pytest.mark.asyncio
async def test_create_typification_conflict(client, create_typification):
    await create_typification(name='Existing Typification')

    response = client.post(
        '/typification/',
        json={'name': 'Existing Typification'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Typification name already exists'}


def test_read_typifications_empty(client):
    response = client.get('/typification/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'typifications': []}


@pytest.mark.asyncio
async def test_read_typifications_with_data(client, create_typification):
    typification = await create_typification(name='Category A')
    typification_schema = TypificationPublic.model_validate(
        typification
    ).model_dump(mode='json')

    response = client.get('/typification/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'typifications': [typification_schema]}


@pytest.mark.asyncio
async def test_read_typification_by_id(client, create_typification):
    typification = await create_typification(name='Specific Typification')
    response = client.get(f'/typification/{typification.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(typification.id)
    assert data['name'] == 'Specific Typification'


def test_read_nonexistent_typification(client):
    response = client.get(f'/typification/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


@pytest.mark.asyncio
async def test_update_typification(client, create_typification):
    typification = await create_typification(name='Old Name')

    response = client.put(
        '/typification/',
        json={
            'id': str(typification.id),
            'name': 'New Name',
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(typification.id)
    assert data['name'] == 'New Name'


@pytest.mark.asyncio
async def test_update_typification_conflict(client, create_typification):
    await create_typification(name='Typification A')
    typification_b = await create_typification(name='Typification B')

    response = client.put(
        '/typification/',
        json={
            'id': str(typification_b.id),
            'name': 'Typification A',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Typification name already exists'}


def test_update_nonexistent_typification(client):
    response = client.put(
        '/typification/',
        json={
            'id': str(uuid.uuid4()),
            'name': 'Ghost Typification',
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


@pytest.mark.asyncio
async def test_delete_typification(client, create_typification):
    typification = await create_typification(name='ToDelete')
    response = client.delete(f'/typification/{typification.id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Typification deleted'}


def test_delete_nonexistent_typification(client):
    response = client.delete(f'/typification/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}
