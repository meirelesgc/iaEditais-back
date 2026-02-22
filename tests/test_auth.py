from http import HTTPStatus
from uuid import uuid4

import pytest

from iaEditais.core.security import create_access_token
from iaEditais.core.settings import Settings

SETTINGS = Settings()


@pytest.mark.asyncio
async def test_login_token_success(client, create_user, create_unit):
    unit = await create_unit()
    await create_user(
        email='joao@auth.com', password='secret', unit_id=str(unit.id)
    )
    response = client.post(
        '/auth/token', data={'username': 'joao@auth.com', 'password': 'secret'}
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'
    token = data['access_token']

    refresh_resp = client.post(
        '/auth/refresh_token', headers={'Authorization': f'Bearer {token}'}
    )
    assert refresh_resp.status_code == HTTPStatus.OK
    new = refresh_resp.json()
    assert 'access_token' in new
    assert new['token_type'] == 'bearer'
    assert new['access_token'] != token


@pytest.mark.asyncio
async def test_login_incorrect_email(client):
    response = client.post(
        '/auth/token', data={'username': 'noone@example.com', 'password': 'x'}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.asyncio
async def test_login_incorrect_password(client, create_user, create_unit):
    unit = await create_unit()
    await create_user(
        email='maria@auth.com', password='rightpass', unit_id=str(unit.id)
    )
    response = client.post(
        '/auth/token',
        data={'username': 'maria@auth.com', 'password': 'wrongpass'},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.asyncio
async def test_refresh_token_invalid_signature(client):
    response = client.post(
        '/auth/refresh_token',
        headers={'Authorization': 'Bearer invalid.token.here'},
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Could not validate credentials'
    assert response.headers.get('www-authenticate') == 'Bearer'


@pytest.mark.asyncio
async def test_refresh_token_user_not_found(client):
    token = create_access_token({'sub': str(uuid4())})
    response = client.post(
        '/auth/refresh_token', headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Could not validate credentials'
    assert response.headers.get('www-authenticate') == 'Bearer'


@pytest.mark.asyncio
async def test_endpoint_requiring_login(logged_client):
    client, token, headers, user = await logged_client(
        email='alice@test.com', password='mypass'
    )


@pytest.mark.asyncio
async def test_sign_in_cookie_success(client, create_user, create_unit):
    unit = await create_unit()
    password = 'secret_cookie_pass'
    email = 'cookie_user@auth.com'

    await create_user(email=email, password=password, unit_id=str(unit.id))

    response = client.post(
        '/auth/sign-in', data={'username': email, 'password': password}
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert 'access_token' in data
    assert data['token_type'] == 'bearer'

    cookie_name = SETTINGS.ACCESS_TOKEN_COOKIE_NAME
    assert cookie_name in response.cookies
    assert response.cookies[cookie_name] == data['access_token']


@pytest.mark.asyncio
async def test_sign_in_incorrect_email(client):
    response = client.post(
        '/auth/sign-in',
        data={'username': 'wrong@email.com', 'password': 'any'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.asyncio
async def test_sign_in_incorrect_password(client, create_user, create_unit):
    unit = await create_unit()
    await create_user(
        email='valid@auth.com', password='correct_pass', unit_id=str(unit.id)
    )

    response = client.post(
        '/auth/sign-in',
        data={'username': 'valid@auth.com', 'password': 'wrong_pass'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.asyncio
async def test_sign_out_clears_cookie(logged_client):
    client, *_ = await logged_client()
    response = client.post('/auth/sign-out')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['message'] == 'signed out'

    cookie_name = SETTINGS.ACCESS_TOKEN_COOKIE_NAME
    set_cookie_header = response.headers.get('set-cookie', '')

    assert cookie_name in set_cookie_header
    assert 'Max-Age=0' in set_cookie_header or 'Expires=' in set_cookie_header
