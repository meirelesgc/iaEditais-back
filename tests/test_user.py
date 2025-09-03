from http import HTTPStatus
from uuid import uuid4

import pytest

from iaEditais.models import AccessType


@pytest.mark.asyncio
async def test_create_user(client, create_unit):
    unit = await create_unit()
    payload = {
        'username': 'joao',
        'email': 'joao@example.com',
        'phone_number': '11988887777',
        'password': 'secret',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }
    response = client.post('/user/', json=payload)
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['username'] == 'joao'
    assert data['email'] == 'joao@example.com'
    assert data['unit_id'] == str(unit.id)


@pytest.mark.asyncio
async def test_create_user_conflict(client, create_user, create_unit):
    unit = await create_unit()
    await create_user(
        email='maria@example.com',
        phone_number='11999990000',
        unit_id=str(unit.id),
    )

    payload = {
        'username': 'maria',
        'email': 'maria@example.com',
        'phone_number': '11999990000',
        'password': 'secret',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }
    response = client.post('/user/', json=payload)
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail'] == 'Email or phone number already registered'
    )


@pytest.mark.asyncio
async def test_read_users(client, create_user, create_unit):
    unit = await create_unit()
    await create_user(
        username='u1',
        email='u1@test.com',
        phone_number='1111',
        unit_id=str(unit.id),
    )
    await create_user(
        username='u2',
        email='u2@test.com',
        phone_number='2222',
        unit_id=str(unit.id),
    )

    response = client.get('/user/?limit=10&offset=0')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['users']) >= 2


@pytest.mark.asyncio
async def test_read_user_by_id(client, create_user, create_unit):
    unit = await create_unit()
    user = await create_user(
        username='pedro',
        email='pedro@test.com',
        phone_number='1234',
        unit_id=str(unit.id),
    )

    response = client.get(f'/user/{user.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(user.id)
    assert data['username'] == 'pedro'


@pytest.mark.asyncio
async def test_read_user_not_found(client):
    response = client.get(f'/user/{uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_update_user(client, create_user, create_unit):
    unit = await create_unit()
    user = await create_user(
        username='antigo',
        email='old@test.com',
        phone_number='5555',
        unit_id=str(unit.id),
    )

    payload = {
        'id': str(user.id),
        'username': 'novo',
        'email': 'new@test.com',
        'phone_number': '6666',
        'password': 'newpass',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }
    response = client.put('/user/', json=payload)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['username'] == 'novo'
    assert data['email'] == 'new@test.com'


@pytest.mark.asyncio
async def test_update_user_not_found(client):
    payload = {
        'id': str(uuid4()),
        'username': 'fake',
        'email': 'fake@test.com',
        'phone_number': '0000',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(uuid4()),
    }
    response = client.put('/user/', json=payload)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_update_user_conflict(client, create_user, create_unit):
    unit = await create_unit()
    await create_user(
        username='u1',
        email='a@test.com',
        phone_number='1111',
        unit_id=str(unit.id),
    )
    user2 = await create_user(
        username='u2',
        email='b@test.com',
        phone_number='2222',
        unit_id=str(unit.id),
    )

    payload = {
        'id': str(user2.id),
        'username': 'u2',
        'email': 'a@test.com',
        'phone_number': '3333',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }
    response = client.put('/user/', json=payload)
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail'] == 'Email or phone number already registered'
    )


@pytest.mark.asyncio
async def test_delete_user(client, create_user, create_unit):
    unit = await create_unit()
    user = await create_user(
        username='to_delete',
        email='del@test.com',
        phone_number='4444',
        unit_id=str(unit.id),
    )

    response = client.delete(f'/user/{user.id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['message'] == 'User deleted'


@pytest.mark.asyncio
async def test_delete_user_not_found(client):
    response = client.delete(f'/user/{uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'User not found'
