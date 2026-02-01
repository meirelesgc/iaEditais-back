import io
from datetime import datetime, timedelta
from http import HTTPStatus
from uuid import uuid4

import pytest
from sqlalchemy import select

from iaEditais.core.security import get_password_hash
from iaEditais.models import AccessType, PasswordReset


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


@pytest.mark.asyncio
async def test_update_user_rejects_password_field(logged_client, create_unit):
    client, token, headers, current_user = await logged_client()
    unit = await create_unit()

    payload = {
        'id': str(current_user.id),
        'username': 'novo_nome',
        'email': 'novo@test.com',
        'phone_number': '6666',
        'password': 'Newpass1',
        'access_level': AccessType.DEFAULT,
        'unit_id': str(unit.id),
    }

    response = client.put('/user/', json=payload)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_change_password_self_success(logged_client):
    client, token, headers, current_user = await logged_client()

    payload = {
        'user_id': str(current_user.id),
        'current_password': 'secret',
        'new_password': 'Newpass1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['message'] == 'Password updated successfully'


@pytest.mark.asyncio
async def test_change_password_self_missing_current_password(logged_client):
    client, token, headers, current_user = await logged_client()

    payload = {
        'user_id': str(current_user.id),
        'new_password': 'Newpass1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Current password is required'


@pytest.mark.asyncio
async def test_change_password_self_invalid_current_password(logged_client):
    client, token, headers, current_user = await logged_client()

    payload = {
        'user_id': str(current_user.id),
        'current_password': 'wrong',
        'new_password': 'Newpass1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Invalid current password'


@pytest.mark.asyncio
async def test_change_password_weak_password(logged_client):
    client, token, headers, current_user = await logged_client()

    payload = {
        'user_id': str(current_user.id),
        'current_password': 'secret',
        'new_password': 'Abc1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert (
        response.json()['detail']
        == 'Password must be at least 8 characters long'
    )


@pytest.mark.asyncio
async def test_change_password_user_not_found(logged_client):
    client, token, headers, current_user = await logged_client()

    payload = {
        'user_id': str(uuid4()),
        'current_password': 'secret',
        'new_password': 'Newpass1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'User not found'


@pytest.mark.asyncio
async def test_change_password_other_user_forbidden(
    logged_client, create_user, create_unit
):
    client, token, headers, current_user = await logged_client()
    unit = await create_unit()

    victim = await create_user(
        username='victim',
        email='victim@test.com',
        phone_number='9999',
        unit_id=str(unit.id),
    )

    payload = {
        'user_id': str(victim.id),
        'current_password': 'secret',
        'new_password': 'Newpass1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert (
        response.json()['detail']
        == 'You are not authorized to change this password'
    )


@pytest.mark.asyncio
async def test_admin_can_change_other_user_password(
    client, create_user, create_unit, logged_client
):
    unit = await create_unit()

    client, token, headers, admin_user = await logged_client(
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
        'user_id': str(target_user.id),
        'new_password': 'Newpass1',
    }

    response = client.put('/user/password', json=payload, headers=headers)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['message'] == 'Password updated successfully'


@pytest.mark.asyncio
async def test_forgot_password_success(
    client, create_user, session, create_unit
):
    unit = await create_unit()
    user = await create_user(
        username='forgot_user',
        email='forgot@example.com',
        phone_number='11999998888',
        unit_id=str(unit.id),
    )

    payload = {'email': 'forgot@example.com'}
    response = client.post('/user/forgot-password', json=payload)

    assert response.status_code == HTTPStatus.OK
    assert (
        response.json()['message']
        == 'If user exists, a code was sent via WhatsApp'
    )

    # Verificação extra: garante que criou o registro no banco
    db_reset = await session.scalar(
        select(PasswordReset).where(PasswordReset.user_id == user.id)
    )
    assert db_reset is not None


@pytest.mark.asyncio
async def test_forgot_password_user_not_found(client):
    payload = {'email': 'naoexiste@example.com'}
    response = client.post('/user/forgot-password', json=payload)

    # Deve retornar 200 OK para evitar enumeração de usuários
    assert response.status_code == HTTPStatus.OK
    assert (
        response.json()['message']
        == 'If user exists, a code was sent via WhatsApp'
    )


@pytest.mark.asyncio
async def test_reset_password_success(
    client, create_user, session, create_unit
):
    unit = await create_unit()
    user = await create_user(
        username='reset_user',
        email='reset@example.com',
        phone_number='11988887777',
        unit_id=str(unit.id),
    )

    # Setup: Criar manualmente um token válido no banco
    raw_token = 'ABC123'
    token_hash = get_password_hash(raw_token)
    expires_at = datetime.now() + timedelta(minutes=15)

    db_reset = PasswordReset(
        user_id=user.id, token_hash=token_hash, expires_at=expires_at
    )
    session.add(db_reset)
    await session.commit()

    payload = {
        'email': user.email,
        'token': raw_token,
        'new_password': 'NewPassword123',
    }
    response = client.post('/user/reset-password', json=payload)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['message'] == 'Password reset successfully'

    await session.refresh(user)
    reset_entry = await session.scalar(
        select(PasswordReset).where(PasswordReset.user_id == user.id)
    )
    assert reset_entry is None


@pytest.mark.asyncio
async def test_reset_password_invalid_token(
    client, create_user, session, create_unit
):
    unit = await create_unit()
    user = await create_user(
        email='wrongtoken@example.com',
        phone_number='11977776666',
        unit_id=str(unit.id),
    )

    token_hash = get_password_hash('ABC123')
    db_reset = PasswordReset(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now() + timedelta(minutes=15),
    )
    session.add(db_reset)
    await session.commit()

    payload = {
        'email': user.email,
        'token': 'WRONG999',
        'new_password': 'NewPassword123',
    }
    response = client.post('/user/reset-password', json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Invalid token'


@pytest.mark.asyncio
async def test_reset_password_expired_token(
    client, create_user, session, create_unit
):
    unit = await create_unit()
    user = await create_user(
        email='expired@example.com',
        phone_number='11966665555',
        unit_id=str(unit.id),
    )

    raw_token = 'EXPIRED'
    token_hash = get_password_hash(raw_token)
    # Data no passado
    past_date = datetime.now() - timedelta(minutes=10)

    db_reset = PasswordReset(
        user_id=user.id, token_hash=token_hash, expires_at=past_date
    )
    session.add(db_reset)
    await session.commit()

    payload = {
        'email': user.email,
        'token': raw_token,
        'new_password': 'NewPassword123',
    }
    response = client.post('/user/reset-password', json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Token expired'


@pytest.mark.asyncio
async def test_reset_password_weak_password(
    client, create_user, session, create_unit
):
    unit = await create_unit()
    user = await create_user(
        email='weakpass@example.com',
        phone_number='11955554444',
        unit_id=str(unit.id),
    )

    raw_token = 'CODE123'
    token_hash = get_password_hash(raw_token)

    db_reset = PasswordReset(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now() + timedelta(minutes=15),
    )
    session.add(db_reset)
    await session.commit()

    payload = {
        'email': user.email,
        'token': raw_token,
        'new_password': '123',
    }
    response = client.post('/user/reset-password', json=payload)
    print(response.json())
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Password requirements not met'


@pytest.mark.asyncio
async def test_reset_password_user_not_found(client):
    payload = {
        'email': 'ghost@example.com',
        'token': 'ANYTOKEN',
        'new_password': 'NewPassword123',
    }
    response = client.post('/user/reset-password', json=payload)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()['detail'] == 'Invalid request'


@pytest.mark.asyncio
async def test_reset_password_no_request_created(
    client, create_user, create_unit
):
    unit = await create_unit()
    user = await create_user(
        email='nopending@example.com',
        phone_number='11944443333',
        unit_id=str(unit.id),
    )

    payload = {
        'email': user.email,
        'token': 'ANYTOKEN',
        'new_password': 'NewPassword123',
    }
    response = client.post('/user/reset-password', json=payload)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()['detail'] == 'Invalid or expired token'
