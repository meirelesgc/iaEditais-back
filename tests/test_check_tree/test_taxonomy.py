import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import TaxonomyPublic


@pytest.mark.asyncio
async def test_create_taxonomy(logged_client, create_typification):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification for Taxonomy')
    response = client.post(
        '/taxonomy,
        json={
            'title': 'New Taxonomy',
            'description': 'A detailed description.',
            'typification_id': str(typification.id),
            'source_ids': [],
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['title'] == 'New Taxonomy'
    assert data['description'] == 'A detailed description.'
    assert 'id' in data


@pytest.mark.asyncio
async def test_create_taxonomy_with_source(
    logged_client, create_typification, create_source
):
    source = await create_source()
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification for Taxonomy')
    response = client.post(
        '/taxonomy,
        json={
            'title': 'New Taxonomy',
            'description': 'A detailed description.',
            'typification_id': str(typification.id),
            'source_ids': [str(source.id)],
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['title'] == 'New Taxonomy'
    assert data['description'] == 'A detailed description.'
    assert 'id' in data


@pytest.mark.asyncio
async def test_create_taxonomy_conflict(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Some Typification')
    await create_taxonomy(
        title='Existing Title', typification_id=typification.id
    )

    response = client.post(
        '/taxonomy,
        json={
            'title': 'Existing Title',
            'description': 'Another description.',
            'typification_id': str(typification.id),
            'source_ids': [],
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Taxonomy title already exists'}


@pytest.mark.asyncio
async def test_create_taxonomy_with_invalid_typification(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/taxonomy,
        json={
            'title': 'Taxonomy with no Typification',
            'description': 'A description.',
            'typification_id': str(uuid.uuid4()),
            'source_ids': [],
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


def test_read_taxonomies_empty(client):
    response = client.get('/taxonomy)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'taxonomies': []}


@pytest.mark.asyncio
async def test_read_taxonomies_with_data(
    client, create_typification, create_taxonomy
):
    typification = await create_typification(name='Typification A')
    taxonomy = await create_taxonomy(
        title='Taxonomy A', typification_id=typification.id
    )
    taxonomy_schema = TaxonomyPublic.model_validate(taxonomy).model_dump(
        mode='json'
    )

    response = client.get('/taxonomy)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'taxonomies': [taxonomy_schema]}


@pytest.mark.asyncio
async def test_read_taxonomy_by_id(
    client, create_typification, create_taxonomy
):
    typification = await create_typification(name='Some Typification')
    taxonomy = await create_taxonomy(
        title='Specific Taxonomy', typification_id=typification.id
    )

    response = client.get(f'/taxonomy/{taxonomy.id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(taxonomy.id)
    assert data['title'] == 'Specific Taxonomy'


def test_read_nonexistent_taxonomy(client):
    response = client.get(f'/taxonomy/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Taxonomy not found'}


@pytest.mark.asyncio
async def test_update_taxonomy(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification1 = await create_typification(name='Old Typification')
    typification2 = await create_typification(name='New Typification')
    taxonomy = await create_taxonomy(
        title='Old Title',
        description='Old desc.',
        typification_id=typification1.id,
    )

    response = client.put(
        '/taxonomy,
        json={
            'id': str(taxonomy.id),
            'title': 'New Title',
            'description': 'New desc.',
            'typification_id': str(typification2.id),
            'source_ids': [],
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(taxonomy.id)
    assert data['title'] == 'New Title'
    assert data['description'] == 'New desc.'


@pytest.mark.asyncio
async def test_update_taxonomy_with_source(
    logged_client, create_typification, create_taxonomy, create_source
):
    client, *_ = await logged_client()
    typification1 = await create_typification(name='Old Typification')
    typification2 = await create_typification(name='New Typification')
    taxonomy = await create_taxonomy(
        title='Old Title',
        description='Old desc.',
        typification_id=typification1.id,
    )

    source = await create_source()

    response = client.put(
        '/taxonomy,
        json={
            'id': str(taxonomy.id),
            'title': 'New Title',
            'description': 'New desc.',
            'typification_id': str(typification2.id),
            'source_ids': [str(source.id)],
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(taxonomy.id)
    assert data['title'] == 'New Title'
    assert data['description'] == 'New desc.'


@pytest.mark.asyncio
async def test_update_taxonomy_conflict(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Some Typification')
    await create_taxonomy(title='Taxonomy A', typification_id=typification.id)
    taxonomy_b = await create_taxonomy(
        title='Taxonomy B', typification_id=typification.id
    )

    response = client.put(
        '/taxonomy,
        json={
            'id': str(taxonomy_b.id),
            'title': 'Taxonomy A',
            'description': taxonomy_b.description,
            'typification_id': str(typification.id),
            'source_ids': [],
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Taxonomy title already exists'}


@pytest.mark.asyncio
async def test_update_nonexistent_taxonomy(logged_client, create_typification):
    client, *_ = await logged_client()
    typification = await create_typification(name='Some typification')
    response = client.put(
        '/taxonomy,
        json={
            'id': str(uuid.uuid4()),
            'title': 'Ghost Taxonomy',
            'description': '...',
            'typification_id': str(typification.id),
            'source_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Taxonomy not found'}


@pytest.mark.asyncio
async def test_update_taxonomy_with_nonexistent_typification(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Some Typification')
    taxonomy = await create_taxonomy(
        title='My Taxonomy', typification_id=typification.id
    )

    response = client.put(
        '/taxonomy,
        json={
            'id': str(taxonomy.id),
            'title': 'New Title',
            'description': 'New Desc',
            'typification_id': str(uuid.uuid4()),
            'source_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}


@pytest.mark.asyncio
async def test_delete_taxonomy(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Some Typification')
    taxonomy = await create_taxonomy(
        title='ToDelete', typification_id=typification.id
    )

    delete_response = client.delete(f'/taxonomy/{taxonomy.id}')
    assert delete_response.status_code == HTTPStatus.NO_CONTENT

    get_response = client.get(f'/taxonomy/{taxonomy.id}')
    assert get_response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_nonexistent_taxonomy(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/taxonomy/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Taxonomy not found'}
