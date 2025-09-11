import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import UnitPublic


def test_create_unit(client):
    response = client.post(
        '/unit/',
        json={
            'name': 'Finance Department',
            'location': 'Headquarters',
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Finance Department'
    assert data['location'] == 'Headquarters'
    assert 'id' in data
    assert 'created_at' in data


def test_read_units_empty(client):
    response = client.get('/unit/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'units': []}


@pytest.mark.asyncio
async def test_read_units_with_data(client, create_unit):
    unit = await create_unit(name='Audit Team', location='São Paulo')
    unit_schema = UnitPublic.model_validate(unit).model_dump(mode='json')

    response = client.get('/unit/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'units': [unit_schema]}


@pytest.mark.asyncio
async def test_read_unit_by_id(client, create_unit):
    unit = await create_unit(name='Analysis Team', location='Brasília')
    response = client.get(f'/unit/{unit.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(unit.id)
    assert data['name'] == 'Analysis Team'


@pytest.mark.asyncio
async def test_update_unit(client, create_unit):
    unit = await create_unit(name='Old Name', location='Rio de Janeiro')

    response = client.put(
        '/unit/',
        json={
            'id': str(unit.id),
            'name': 'New Name',
            'location': 'Rio',
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(unit.id)
    assert data['name'] == 'New Name'
    assert data['location'] == 'Rio'


@pytest.mark.asyncio
async def test_update_unit_conflict(client, create_unit):
    await create_unit(name='Unit A', location='SP')
    unit2 = await create_unit(name='Unit B', location='RJ')

    response = client.put(
        '/unit/',
        json={
            'id': str(unit2.id),
            'name': 'Unit A',
            'location': 'RJ',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Unit name already exists'}


@pytest.mark.asyncio
async def test_delete_unit(client, create_unit):
    unit = await create_unit(name='ToDelete', location='BH')
    response = client.delete(f'/unit/{unit.id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Unit deleted'}


def test_read_nonexistent_unit(client):
    response = client.get(f'/unit/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Unit not found'}


def test_update_nonexistent_unit(client):
    response = client.put(
        '/unit/',
        json={
            'id': str(uuid.uuid4()),
            'name': 'Ghost Unit',
            'location': 'Nowhere',
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Unit not found'}


def test_delete_nonexistent_unit(client):
    response = client.delete(f'/unit/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Unit not found'}
