from http import HTTPStatus
from pathlib import Path

import pytest

from iaEditais.models import source_model
from tests.factories import source_factory


def test_post_source(client):
    source = source_factory.CreateSourceFactory()

    response = client.post('/source/', json=source.model_dump(mode='json'))

    assert response.status_code == HTTPStatus.CREATED
    assert source_model.Source(**response.json())


@pytest.mark.asyncio
async def test_source_post_upload(client, create_source):
    source = await create_source()
    path = Path('tests/storage/sample.pdf')

    with path.open('rb') as payload:
        file = {'file': ('sample.pdf', payload, 'application/pdf')}
        response = client.post(f'/source/{source.id}/upload/', files=file)
    assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_source_get_id(client, create_source):
    source = await create_source()
    response = client.get(f'/source/{source.id}/')
    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == str(source.id)


@pytest.mark.asyncio
async def test_source_get(client, create_source):
    AMONG = 1
    for _ in range(AMONG):
        await create_source()

    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG


@pytest.mark.asyncio
async def test_source_get_any_sources(client, create_source):
    AMONG = 10
    for _ in range(AMONG):
        await create_source()

    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMONG


@pytest.mark.asyncio
async def test_source_put(client, create_source):
    source = await create_source()
    source.name = 'New source name'

    response = client.put(
        '/source/',
        json=source.model_dump(mode='json'),
    )
    assert response.status_code == HTTPStatus.OK
    assert 'updated_at' in response.json()


@pytest.mark.asyncio
async def test_get_upload(client, create_source_with_upload):
    source = await create_source_with_upload()
    response = client.get(f'/source/{source.id}/upload/')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'application/pdf'
    assert response.content.startswith(b'%PDF')


@pytest.mark.asyncio
async def test_delete_source(client, create_source):
    source = await create_source()
    response = client.delete(f'/source/{source.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_delete_source_with_upload(client, create_source_with_upload):
    source = await create_source_with_upload()
    response = client.delete(f'/source/{source.id}/upload/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(f'/source/{source.id}/')
    assert response.status_code == HTTPStatus.OK
    assert not response.json().get('has_file')
