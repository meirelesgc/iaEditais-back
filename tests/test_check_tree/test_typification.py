import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import TypificationPublic


@pytest.mark.asyncio
async def test_create_typification(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/typification,
        json={'name': 'Financial Reports', 'source_ids': []},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Financial Reports'
    assert data['sources'] == []


@pytest.mark.asyncio
async def test_create_typification_with_source(logged_client, create_source):
    source = await create_source()
    client, *_ = await logged_client()
    response = client.post(
        '/typification,
        json={'name': 'Financial Reports', 'source_ids': [str(source.id)]},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Financial Reports'
    assert data['sources'][0]['name'] == source.name


@pytest.mark.asyncio
async def test_create_typification_conflict(
    logged_client, create_typification
):
    client, *_ = await logged_client()
    await create_typification(name='Existing Typification')

    response = client.post(
        '/typification,
        json={'name': 'Existing Typification', 'source_ids': []},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Typification name already exists'}


def test_read_typifications_empty(client):
    response = client.get('/typification)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'typifications': []}


@pytest.mark.asyncio
async def test_read_typifications_with_data(client, create_typification):
    typification = await create_typification(name='Category A')
    typification_schema = TypificationPublic.model_validate(
        typification
    ).model_dump(mode='json')

    response = client.get('/typification)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'typifications': [typification_schema]}


@pytest.mark.asyncio
async def test_read_typification_by_id(client, create_typification):
    typification = await create_typification(name='Specific Typification')
    response = client.get(f'/typification/{typification.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(typification.id)
    assert data['name'] == 'Specific Typification'


def test_read_nonexistent_typification(client):
    response = client.get(f'/typification/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


@pytest.mark.asyncio
async def test_update_typification(logged_client, create_typification):
    client, *_ = await logged_client()
    typification = await create_typification(name='Old Name')

    response = client.put(
        '/typification,
        json={
            'id': str(typification.id),
            'name': 'New Name',
            'source_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(typification.id)
    assert data['name'] == 'New Name'


@pytest.mark.asyncio
async def test_update_typification_updated_at_lazy_load_error(
    logged_client, create_typification, create_source
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Old Name')
    source = await create_source()

    response = client.put(
        '/typification,
        json={
            'id': str(typification.id),
            'name': 'New Name',
            'source_ids': [str(source.id)],
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(typification.id)
    assert data['name'] == 'New Name'


@pytest.mark.asyncio
async def test_update_typification_conflict(
    logged_client, create_typification
):
    client, *_ = await logged_client()
    await create_typification(name='Typification A')
    typification_b = await create_typification(name='Typification B')

    response = client.put(
        '/typification,
        json={
            'id': str(typification_b.id),
            'name': 'Typification A',
            'source_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Typification name already exists'}


@pytest.mark.asyncio
async def test_update_nonexistent_typification(logged_client):
    client, *_ = await logged_client()
    response = client.put(
        '/typification,
        json={
            'id': str(uuid.uuid4()),
            'name': 'Ghost Typification',
            'source_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


@pytest.mark.asyncio
async def test_delete_typification(logged_client, create_typification):
    client, *_ = await logged_client()
    typification = await create_typification(name='ToDelete')
    response = client.delete(f'/typification/{typification.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_delete_nonexistent_typification(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/typification/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


@pytest.mark.asyncio
async def test_listing_taxonomies_typification(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification()
    await create_taxonomy(typification_id=typification.id)

    response = client.get('/typification)
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['typifications'][0]['taxonomies'][0]['id']
