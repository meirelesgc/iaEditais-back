from http import HTTPStatus

import pytest

from tests.factories import user_unit_factory


@pytest.mark.asyncio
async def test_user_unit_post(client, create_user, create_unit):
    user = await create_user()
    unit = await create_unit()
    user_unit = user_unit_factory.CreateUserUnitFactory(
        user_id=user.id, unit_id=unit.id
    )

    response = client.post(
        '/user_units/', json=user_unit.model_dump(mode='json')
    )
    assert response.status_code == HTTPStatus.CREATED
    assert response.json() == {'message': 'User linked to Unit successfully'}


@pytest.mark.asyncio
async def test_user_unit_delete(client, create_user, create_unit):
    user = await create_user()
    unit = await create_unit()
    user_unit = user_unit_factory.CreateUserUnitFactory(
        user_id=user.id, unit_id=unit.id
    )

    client.post('/user_units/', json=user_unit.model_dump(mode='json'))

    response = client.delete(
        '/user_units/', params={'user_id': user.id, 'unit_id': unit.id}
    )
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_user_unit_get_user(client, create_user, create_unit):
    AMONG = 3
    user = await create_user()
    units = [await create_unit() for _ in range(AMONG)]
    for unit in units:
        client.post(
            '/user_units/',
            json={'user_id': str(user.id), 'unit_id': str(unit.id)},
        )

    response = client.get(f'/user_units/user/{user.id}/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG


@pytest.mark.asyncio
async def test_user_unit_get_unity(client, create_user, create_unit):
    AMONG = 3
    users = [await create_user() for _ in range(AMONG)]
    unit = await create_unit()
    for user in users:
        client.post(
            '/user_units/',
            json={'user_id': str(user.id), 'unit_id': str(unit.id)},
        )

    response = client.get(f'/user_units/unit/{unit.id}/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG
