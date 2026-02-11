import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas import BranchPublic


@pytest.mark.asyncio
async def test_create_branch(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification for Branch')
    taxonomy = await create_taxonomy(
        title='Taxonomy for Branch', typification_id=typification.id
    )
    response = client.post(
        '/branch',
        json={
            'title': 'New Branch',
            'description': 'A branch description.',
            'taxonomy_id': str(taxonomy.id),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['title'] == 'New Branch'
    assert data['description'] == 'A branch description.'
    assert 'id' in data


@pytest.mark.asyncio
async def test_create_branch_with_other_tax(
    logged_client, create_typification, create_taxonomy, create_branch
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification for Branch')
    taxonomy_a = await create_taxonomy(
        title='Taxonomy A', typification_id=typification.id
    )
    await create_branch(title='Branch A', taxonomy_id=taxonomy_a.id)

    taxonomy_b = await create_taxonomy(
        title='Taxonomy B', typification_id=typification.id
    )

    response = client.post(
        '/branch',
        json={
            'title': 'Branch A',
            'description': 'A branch description.',
            'taxonomy_id': str(taxonomy_b.id),
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['title'] == 'Branch A'
    assert data['description'] == 'A branch description.'
    assert 'id' in data


@pytest.mark.asyncio
async def test_create_branch_conflict(
    logged_client, create_typification, create_taxonomy, create_branch
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification A')
    taxonomy = await create_taxonomy(
        title='Taxonomy A', typification_id=typification.id
    )
    await create_branch(title='Existing Branch', taxonomy_id=taxonomy.id)

    response = client.post(
        '/branch',
        json={
            'title': 'Existing Branch',
            'description': 'Another desc.',
            'taxonomy_id': str(taxonomy.id),
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Branch title already exists for this taxonomy'
    }


@pytest.mark.asyncio
async def test_create_branch_with_invalid_taxonomy(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/branch',
        json={
            'title': 'Invalid Branch',
            'description': 'desc',
            'taxonomy_id': str(uuid.uuid4()),
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Taxonomy not found'}


def test_read_branches_empty(client):
    response = client.get('/branch')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'branches': []}


@pytest.mark.asyncio
async def test_read_branches_with_data(
    client, create_typification, create_taxonomy, create_branch
):
    typification = await create_typification(name='Typification B')
    taxonomy = await create_taxonomy(
        title='Taxonomy B', typification_id=typification.id
    )
    branch = await create_branch(title='Branch A', taxonomy_id=taxonomy.id)
    branch_schema = BranchPublic.model_validate(branch).model_dump(mode='json')

    response = client.get('/branch')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'branches': [branch_schema]}


@pytest.mark.asyncio
async def test_read_branch_by_id(
    client, create_typification, create_taxonomy, create_branch
):
    typification = await create_typification(name='Typification C')
    taxonomy = await create_taxonomy(
        title='Taxonomy C', typification_id=typification.id
    )
    branch = await create_branch(
        title='Specific Branch', taxonomy_id=taxonomy.id
    )

    response = client.get(f'/branch/{branch.id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(branch.id)
    assert data['title'] == 'Specific Branch'


def test_read_nonexistent_branch(client):
    response = client.get(f'/branch/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Branch not found'}


@pytest.mark.asyncio
async def test_update_branch(
    logged_client, create_typification, create_taxonomy, create_branch
):
    client, *_ = await logged_client()
    typification1 = await create_typification(name='Typification X')
    taxonomy1 = await create_taxonomy(
        title='Taxonomy X', typification_id=typification1.id
    )
    typification2 = await create_typification(name='Typification Y')
    taxonomy2 = await create_taxonomy(
        title='Taxonomy Y', typification_id=typification2.id
    )
    branch = await create_branch(
        title='Old Branch',
        description='Old desc.',
        taxonomy_id=taxonomy1.id,
    )

    response = client.put(
        '/branch',
        json={
            'id': str(branch.id),
            'title': 'Updated Branch',
            'description': 'New desc.',
            'taxonomy_id': str(taxonomy2.id),
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(branch.id)
    assert data['title'] == 'Updated Branch'
    assert data['description'] == 'New desc.'


@pytest.mark.asyncio
async def test_update_branch_conflict(
    logged_client, create_typification, create_taxonomy, create_branch
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification D')
    taxonomy = await create_taxonomy(
        title='Taxonomy D', typification_id=typification.id
    )
    await create_branch(title='Branch A', taxonomy_id=taxonomy.id)
    branch_b = await create_branch(title='Branch B', taxonomy_id=taxonomy.id)

    response = client.put(
        '/branch',
        json={
            'id': str(branch_b.id),
            'title': 'Branch A',
            'description': branch_b.description,
            'taxonomy_id': str(taxonomy.id),
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Branch title already exists for this taxonomy'
    }


@pytest.mark.asyncio
async def test_update_nonexistent_branch(
    logged_client, create_typification, create_taxonomy
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification E')
    taxonomy = await create_taxonomy(
        title='Taxonomy E', typification_id=typification.id
    )
    response = client.put(
        '/branch',
        json={
            'id': str(uuid.uuid4()),
            'title': 'Ghost Branch',
            'description': '...',
            'taxonomy_id': str(taxonomy.id),
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Branch not found'}


@pytest.mark.asyncio
async def test_update_branch_with_nonexistent_taxonomy(
    logged_client, create_typification, create_taxonomy, create_branch
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification F')
    taxonomy = await create_taxonomy(
        title='Taxonomy F', typification_id=typification.id
    )
    branch = await create_branch(title='Branch F', taxonomy_id=taxonomy.id)

    response = client.put(
        '/branch',
        json={
            'id': str(branch.id),
            'title': 'Updated Title',
            'description': 'Updated Desc',
            'taxonomy_id': str(uuid.uuid4()),
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Taxonomy not found'}


@pytest.mark.asyncio
async def test_delete_branch(
    logged_client, create_typification, create_taxonomy, create_branch
):
    client, *_ = await logged_client()
    typification = await create_typification(name='Typification G')
    taxonomy = await create_taxonomy(
        title='Taxonomy G', typification_id=typification.id
    )
    branch = await create_branch(
        title='Branch to Delete', taxonomy_id=taxonomy.id
    )

    delete_response = client.delete(f'/branch/{branch.id}')
    assert delete_response.status_code == HTTPStatus.NO_CONTENT

    get_response = client.get(f'/branch/{branch.id}')
    assert get_response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_nonexistent_branch(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/branch/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Branch not found'}
