from http import HTTPStatus

import pytest

from iaEditais.models import unit_model
from tests.factories import unit_factory


def test_unit_post(client):
    unit = unit_factory.CreateUnitFactory()
    response = client.post('/unit/', json=unit.model_dump(mode='json'))
    assert response.status_code == HTTPStatus.CREATED
    assert unit_model.UnitResponse(**response.json())


@pytest.mark.asyncio
async def test_unit_get(client, create_unit):
    AMONG = 1

    for _ in range(AMONG):
        await create_unit()

    response = client.get('/unit/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG


@pytest.mark.asyncio
async def test_unit_get_two(client, create_unit):
    AMONG = 2

    for _ in range(AMONG):
        await create_unit()

    response = client.get('/unit/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG


@pytest.mark.asyncio
async def test_unit_get_detail(client, create_unit):
    unit = await create_unit()

    response = client.get(f'/unit/{unit.id}/')
    assert response.status_code == HTTPStatus.OK
    assert unit_model.Unit(**response.json())
