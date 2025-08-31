import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import UnitPublic


def test_create_unit(client):
    response = client.post(
        '/units/',
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
    response = client.get('/units/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'units': []}


@pytest.mark.asyncio
async def test_read_units_with_data(client, create_unit):
    unit = await create_unit(name='Audit Team', location='São Paulo')
    unit_schema = UnitPublic.model_validate(unit).model_dump(mode='json')

    response = client.get('/units/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'units': [unit_schema]}


@pytest.mark.asyncio
async def test_read_unit_by_id(client, create_unit):
    unit = await create_unit(name='Analysis Team', location='Brasília')
    response = client.get(f'/units/{unit.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(unit.id)
    assert data['name'] == 'Analysis Team'


@pytest.mark.asyncio
async def test_update_unit(client, create_unit):
    unit = await create_unit(name='Old Name', location='Rio de Janeiro')

    response = client.put(
        f'/units/{unit.id}',
        json={
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
    unit1 = await create_unit(name='Unit A', location='SP')
    unit2 = await create_unit(name='Unit B', location='RJ')

    response = client.put(
        f'/units/{unit2.id}',
        json={
            'name': 'Unit A',
            'location': 'RJ',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Unit name already exists'}


@pytest.mark.asyncio
async def test_delete_unit(client, create_unit):
    unit = await create_unit(name='ToDelete', location='BH')
    response = client.delete(f'/units/{unit.id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Unit deleted'}


def test_read_nonexistent_unit(client):
    response = client.get(f'/units/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Unit not found'}


def test_update_nonexistent_unit(client):
    response = client.put(
        f'/units/{uuid.uuid4()}',
        json={
            'name': 'Ghost Unit',
            'location': 'Nowhere',
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Unit not found'}


def test_delete_nonexistent_unit(client):
    response = client.delete(f'/units/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Unit not found'}
