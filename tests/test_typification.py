from http import HTTPStatus

import pytest

from iaEditais.models import typification_model
from tests.factories import typification_factory


def test_post_typification(client):
    typification = typification_factory.CreateTypificationFactory()

    response = client.post(
        '/typification/', json=typification.model_dump(mode='json')
    )

    assert response.status_code == HTTPStatus.CREATED
    assert typification_model.Typification(**response.json())


@pytest.mark.asyncio
async def test_get_typification_by_id(client, create_typification):
    typification = await create_typification()

    response = client.get(f'/typification/{typification.id}/')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == str(typification.id)


@pytest.mark.asyncio
async def test_get_typification_list(client, create_typification):
    AMONG = 5
    for _ in range(AMONG):
        await create_typification()

    response = client.get('/typification/')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG


@pytest.mark.asyncio
async def test_put_typification(client, create_typification):
    typification = await create_typification()
    typification.name = 'Updated Typification Name'

    response = client.put(
        '/typification/', json=typification.model_dump(mode='json')
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['name'] == 'Updated Typification Name'
    assert 'updated_at' in response.json()


@pytest.mark.asyncio
async def test_delete_typification(client, create_typification):
    typification = await create_typification()

    response = client.delete(f'/typification/{typification.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(f'/typification/{typification.id}/')
    assert response.status_code == HTTPStatus.NOT_FOUND
