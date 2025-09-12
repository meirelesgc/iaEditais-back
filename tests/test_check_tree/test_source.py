import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import SourcePublic


@pytest.mark.asyncio
async def test_create_source(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/source/',
        json={
            'name': 'Official Government Gazette',
            'description': 'Primary source for official announcements.',
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Official Government Gazette'
    assert data['description'] == 'Primary source for official announcements.'
    assert 'id' in data
    assert 'created_at' in data


@pytest.mark.asyncio
async def test_create_source_conflict(logged_client, create_source):
    client, *_ = await logged_client()
    await create_source(name='Existing Source')

    response = client.post(
        '/source/',
        json={
            'name': 'Existing Source',
            'description': 'A duplicate entry.',
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Source name already exists'}


def test_read_sources_empty(client):
    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'sources': []}


@pytest.mark.asyncio
async def test_read_sources_with_data(client, create_source):
    source = await create_source(
        name='Source One', description='Description One'
    )
    source_schema = SourcePublic.model_validate(source).model_dump(mode='json')

    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'sources': [source_schema]}


@pytest.mark.asyncio
async def test_read_source_by_id(client, create_source):
    source = await create_source(
        name='Specific Source', description='Details here'
    )
    response = client.get(f'/source/{source.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(source.id)
    assert data['name'] == 'Specific Source'


def test_read_nonexistent_source(client):
    response = client.get(f'/source/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Source not found'}


@pytest.mark.asyncio
async def test_update_source(logged_client, create_source):
    client, *_ = await logged_client()
    source = await create_source(
        name='Old Name', description='Old Description'
    )

    response = client.put(
        '/source/',
        json={
            'id': str(source.id),
            'name': 'New Name',
            'description': 'New Description',
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(source.id)
    assert data['name'] == 'New Name'
    assert data['description'] == 'New Description'


@pytest.mark.asyncio
async def test_update_source_conflict(logged_client, create_source):
    client, *_ = await logged_client()
    await create_source(name='Source A', description='First source')
    source_b = await create_source(
        name='Source B', description='Second source'
    )

    response = client.put(
        '/source/',
        json={
            'id': str(source_b.id),
            'name': 'Source A',
            'description': 'Updated description',
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Source name already exists'}


@pytest.mark.asyncio
async def test_update_nonexistent_source(logged_client):
    client, *_ = await logged_client()
    response = client.put(
        '/source/',
        json={
            'id': str(uuid.uuid4()),
            'name': 'Ghost Source',
            'description': 'This does not exist.',
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Source not found'}


@pytest.mark.asyncio
async def test_delete_source(logged_client, create_source):
    client, *_ = await logged_client()
    source = await create_source(name='ToDelete', description='Will be gone')
    response = client.delete(f'/source/{source.id}')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Source deleted'}


@pytest.mark.asyncio
async def test_delete_nonexistent_source(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/source/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Source not found'}
