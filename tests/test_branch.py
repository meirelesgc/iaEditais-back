from http import HTTPStatus

import pytest

from tests.factories import branch_factory


@pytest.mark.asyncio
async def test_post_branch(client, create_taxonomy, create_typification):
    typification = await create_typification()
    taxonomy = await create_taxonomy(typification)

    branch = branch_factory.CreateBranchFactory(taxonomy_id=taxonomy.id)

    response = client.post(
        '/taxonomy/branch/', json=branch.model_dump(mode='json')
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['taxonomy_id'] == str(taxonomy.id)


@pytest.mark.asyncio
async def test_get_branches_by_taxonomy(
    client, create_taxonomy, create_typification, create_branch
):
    typification = await create_typification()
    taxonomy = await create_taxonomy(typification)
    AMOUNT = 3
    for _ in range(AMOUNT):
        await create_branch(taxonomy)

    response = client.get(f'/taxonomy/branch/{taxonomy.id}/')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == AMOUNT
    assert all(
        branch['taxonomy_id'] == str(taxonomy.id) for branch in response.json()
    )


@pytest.mark.asyncio
async def test_put_branch(
    client, create_taxonomy, create_typification, create_branch
):
    typification = await create_typification()
    taxonomy = await create_taxonomy(typification)
    branch = await create_branch(taxonomy)
    branch.title = 'Updated branch name'

    response = client.put(
        '/taxonomy/branch/', json=branch.model_dump(mode='json')
    )

    assert response.status_code == HTTPStatus.OK
    assert response.json()['title'] == 'Updated branch name'


@pytest.mark.asyncio
async def test_delete_branch(
    client, create_taxonomy, create_typification, create_branch
):
    typification = await create_typification()
    taxonomy = await create_taxonomy(typification)
    branch = await create_branch(taxonomy)

    response = client.delete(f'/taxonomy/branch/{branch.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(f'/taxonomy/branch/{taxonomy.id}/')
    assert branch.id not in [b['id'] for b in response.json()]
