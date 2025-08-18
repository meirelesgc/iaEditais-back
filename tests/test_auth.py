from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_login_success(client, create_user):
    user = await create_user()
    data = {'username': user.email, 'password': user.password}
    response = client.post('/auth/login', data=data)
    token = response.json()

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in token
    assert 'token_type' in token
    assert 'access_token' in response.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, create_user):
    user = await create_user()
    data = {'username': user.email, 'password': 'wrongpass'}
    response = client.post('/auth/login', data=data)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Incorrect email or password'


@pytest.mark.asyncio
async def test_refresh_login_success(client, create_user, get_token):
    user = await create_user()
    token = get_token(user)
    client.cookies.set('access_token', token)

    response = client.post('/auth/refresh_login')
    data = response.json()

    assert response.status_code == HTTPStatus.OK
    assert 'access_token' in data
    assert data['token_type'] == 'bearer'
    assert 'access_token' in response.cookies


@pytest.mark.asyncio
async def test_refresh_login_unauthorized(client):
    response = client.post('/auth/refresh_login')

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()['detail'] == 'Not authenticated'


@pytest.mark.asyncio
async def test_logout_success(client, create_user, get_token):
    user = await create_user()
    token = get_token(user)
    client.cookies.set('access_token', token)

    response = client.post('/auth/logout')
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert 'access_token' not in response.cookies
