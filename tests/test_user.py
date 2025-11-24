import io
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
    EXPECTED_MIN_USERS = 2
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
    assert len(data['users']) >= EXPECTED_MIN_USERS


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
async def test_update_user_not_found(logged_client):
    client, *_ = await logged_client()

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
async def test_update_user_self(logged_client, create_unit):
    client, token, headers, current_user = await logged_client()
    unit = await create_unit()

    payload = {
        'id': str(current_user.id),
        'username': 'novo_nome',
        'email': 'novo@test.com',
        'phone_number': '6666',
        'password': 'newpass',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }

    response = client.put('/user/', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['username'] == 'novo_nome'
    assert data['email'] == 'novo@test.com'


@pytest.mark.asyncio
async def test_update_user_conflict(logged_client, create_user, create_unit):
    client, token, headers, current_user = await logged_client()
    unit = await create_unit()

    await create_user(
        username='u1',
        email='existe@test.com',
        phone_number='1111',
        unit_id=str(unit.id),
    )

    payload = {
        'id': str(current_user.id),
        'username': 'existe',
        'email': 'existe@test.com',
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
async def test_delete_user(logged_client, create_user, create_unit):
    client, *_ = await logged_client()

    unit = await create_unit()
    user = await create_user(
        username='to_delete',
        email='del@test.com',
        phone_number='4444',
        unit_id=str(unit.id),
    )

    response = client.delete(f'/user/{user.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_delete_user_not_found(logged_client):
    client, *_ = await logged_client()

    response = client.delete(f'/user/{uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_add_icon_success(logged_client):
    client, token, headers, user = await logged_client()

    # Simulate a PNG file upload
    file_content = io.BytesIO(b'fake image content')
    response = client.post(
        f'/user/{user.id}/icon',
        files={'file': ('test.png', file_content, 'image/png')},
        headers=headers,
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['message'] == 'Icon updated successfully'


@pytest.mark.asyncio
async def test_add_icon_invalid_format(logged_client):
    client, token, headers, user = await logged_client()

    file_content = io.BytesIO(b'fake content')
    response = client.post(
        f'/user/{user.id}/icon',
        files={'file': ('test.txt', file_content, 'text/plain')},
        headers=headers,
    )

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Invalid file format. Use PNG or JPG'


@pytest.mark.asyncio
async def test_add_icon_user_not_found(logged_client):
    client, token, headers, _ = await logged_client()

    file_content = io.BytesIO(b'fake image content')
    response = client.post(
        f'/user/{uuid4()}/icon',
        files={'file': ('test.png', file_content, 'image/png')},
        headers=headers,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_delete_icon_success(logged_client):
    client, token, headers, user = await logged_client()

    file_content = io.BytesIO(b'fake image content')
    client.post(
        f'/user/{user.id}/icon',
        files={'file': ('test.png', file_content, 'image/png')},
        headers=headers,
    )

    response = client.delete(f'/user/{user.id}/icon', headers=headers)
    assert response.status_code == HTTPStatus.OK
    assert response.json()['message'] == 'Icon successfully deleted!'


@pytest.mark.asyncio
async def test_delete_icon_not_found(logged_client):
    client, token, headers, user = await logged_client()

    response = client.delete(f'/user/{user.id}/icon', headers=headers)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'Icon not found'


@pytest.mark.asyncio
async def test_update_other_user_forbidden(
    logged_client, create_user, create_unit
):
    client, *_ = await logged_client()
    unit = await create_unit()

    victim = await create_user(
        username='victim',
        email='victim@test.com',
        phone_number='9999',
        unit_id=str(unit.id),
    )

    payload = {
        'id': str(victim.id),
        'username': 'hacked',
        'email': 'hacked@test.com',
        'phone_number': '0000',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }

    response = client.put('/user/', json=payload)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert (
        response.json()['detail']
        == 'You are not authorized to update this user'
    )


@pytest.mark.asyncio
async def test_update_user_cannot_change_access_level(
    logged_client, create_unit
):
    client, token, headers, current_user = await logged_client()
    unit = await create_unit()

    payload = {
        'id': str(current_user.id),
        'username': current_user.username,
        'email': current_user.email,
        'phone_number': current_user.phone_number,
        'access_level': AccessType.ADMIN,
        'unit_id': str(unit.id),
    }

    response = client.put('/user/', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['access_level'] != AccessType.ADMIN
    assert data['access_level'] == AccessType.DEFAULT


@pytest.mark.asyncio
async def test_admin_can_update_other_user_and_access_level(
    client, create_user, create_unit, logged_client
):
    unit = await create_unit()

    client, token, *_ = await logged_client(
        username='admin',
        email='admin@test.com',
        phone_number='8888',
        access_level=AccessType.ADMIN,
    )

    target_user = await create_user(
        username='target',
        email='target@test.com',
        phone_number='9999',
        unit_id=str(unit.id),
    )

    payload = {
        'id': str(target_user.id),
        'username': 'target_updated',
        'email': 'target@test.com',
        'phone_number': '9999',
        'access_level': AccessType.ANALYST,
    }

    response = client.put('/user/', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['username'] == 'target_updated'
    assert data['access_level'] == AccessType.ANALYST
