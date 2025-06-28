from http import HTTPStatus

import pytest

from tests.factories import taxonomy_factory


@pytest.mark.asyncio
async def test_post_taxonomy(client, create_typification):
    typification = await create_typification()
    taxonomy = taxonomy_factory.CreateTaxonomyFactory(
        typification_id=typification.id
    )

    response = client.post('/taxonomy/', json=taxonomy.model_dump(mode='json'))

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['typification_id'] == str(typification.id)


@pytest.mark.asyncio
async def test_get_all_taxonomies(client, create_typification, create_taxonomy):
    AMOUNT = 3

    typification = await create_typification()

    for _ in range(AMOUNT):
        await create_taxonomy(typification)

    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMOUNT


@pytest.mark.asyncio
async def test_get_taxonomies_by_typification(
    client, create_typification, create_taxonomy
):
    typification = await create_typification()
    AMOUNT = 2
    for _ in range(AMOUNT):
        await create_taxonomy(typification)

    response = client.get(f'/taxonomy/{typification.id}/')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMOUNT


@pytest.mark.asyncio
async def test_put_taxonomy(client, create_typification, create_taxonomy):
    typification = await create_typification()
    taxonomy = await create_taxonomy(typification)
    taxonomy.title = 'Updated title'

    response = client.put('/taxonomy/', json=taxonomy.model_dump(mode='json'))

    assert response.status_code == HTTPStatus.OK
    assert response.json()['title'] == 'Updated title'
    assert 'updated_at' in response.json()


@pytest.mark.asyncio
async def test_delete_taxonomy(client, create_typification, create_taxonomy):
    typification = await create_typification()
    taxonomy = await create_taxonomy(typification)

    response = client.delete(f'/taxonomy/{taxonomy.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(f'/taxonomy/{typification.id}/')
    assert taxonomy.id not in [t['id'] for t in response.json()]
