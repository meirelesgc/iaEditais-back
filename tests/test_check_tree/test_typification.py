import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import TypificationPublic


@pytest.mark.asyncio
async def test_create_typification(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/typification',
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
        '/typification',
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
        '/typification',
        json={'name': 'Existing Typification', 'source_ids': []},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Typification name already exists'}


def test_read_typifications_empty(client):
    response = client.get('/typification')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'typifications': []}


@pytest.mark.asyncio
async def test_read_typifications_with_data(client, create_typification):
    typification = await create_typification(name='Category A')
    typification_schema = TypificationPublic.model_validate(
        typification
    ).model_dump(mode='json')

    response = client.get('/typification')
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
        '/typification',
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
        '/typification',
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
        '/typification',
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
        '/typification',
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

    response = client.get('/typification')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['typifications'][0]['taxonomies'][0]['id']


@pytest.mark.asyncio
async def test_clone_typification_without_children(
    logged_client, create_typification
):
    client, *_ = await logged_client()
    original = await create_typification(name='Original')

    response = client.post(f'/typification/{original.id}/clone', json={})

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Cópia de Original'
    assert data['id'] != str(original.id)
    assert data['sources'] == []
    assert data['taxonomies'] == []


@pytest.mark.asyncio
async def test_clone_typification_with_sources(
    logged_client, create_typification, create_source
):
    source = await create_source()
    client, *_ = await logged_client()
    original = await create_typification(
        name='Com Fonte', source_ids=[source.id]
    )

    response = client.post(f'/typification/{original.id}/clone', json={})

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert [s['id'] for s in data['sources']] == [str(source.id)]


@pytest.mark.asyncio
async def test_clone_typification_copies_taxonomies_and_branches(
    logged_client,
    create_typification,
    create_taxonomy,
    create_branch,
):
    client, *_ = await logged_client()
    original = await create_typification(name='Arvore Completa')
    taxonomy = await create_taxonomy(
        typification_id=original.id, title='Taxonomia Original'
    )
    branch = await create_branch(
        taxonomy_id=taxonomy.id, title='Ramo Original'
    )

    response = client.post(f'/typification/{original.id}/clone', json={})
    assert response.status_code == HTTPStatus.CREATED

    cloned_id = response.json()['id']

    detail = client.get(f'/typification/{cloned_id}')
    assert detail.status_code == HTTPStatus.OK
    cloned = detail.json()

    assert len(cloned['taxonomies']) == 1
    cloned_tax = cloned['taxonomies'][0]
    assert cloned_tax['id'] != str(taxonomy.id)
    assert cloned_tax['title'] == 'Taxonomia Original'
    assert cloned_tax['typification_id'] == cloned_id

    assert len(cloned_tax['branches']) == 1
    cloned_branch = cloned_tax['branches'][0]
    assert cloned_branch['id'] != str(branch.id)
    assert cloned_branch['title'] == 'Ramo Original'
    assert cloned_branch['taxonomy_id'] == cloned_tax['id']


@pytest.mark.asyncio
async def test_clone_typification_with_custom_name(
    logged_client, create_typification
):
    client, *_ = await logged_client()
    original = await create_typification(name='Original')

    response = client.post(
        f'/typification/{original.id}/clone', json={'name': 'Nome Custom'}
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['name'] == 'Nome Custom'


@pytest.mark.asyncio
async def test_clone_typification_name_conflict_appends_counter(
    logged_client, create_typification
):
    client, *_ = await logged_client()
    original = await create_typification(name='Original')

    first = client.post(f'/typification/{original.id}/clone', json={})
    second = client.post(f'/typification/{original.id}/clone', json={})

    assert first.status_code == HTTPStatus.CREATED
    assert second.status_code == HTTPStatus.CREATED
    assert first.json()['name'] == 'Cópia de Original'
    assert second.json()['name'] == 'Cópia de Original (1)'


@pytest.mark.asyncio
async def test_clone_nonexistent_typification(logged_client):
    client, *_ = await logged_client()
    response = client.post(f'/typification/{uuid.uuid4()}/clone', json={})
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Typification not found'}
