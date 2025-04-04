from http import HTTPStatus
from datetime import datetime
from iaEditais.schemas.branch import Branch


def test_create_branch(client, create_branch):
    response = create_branch()

    assert response.status_code == HTTPStatus.CREATED
    branch = response.json()
    assert isinstance(Branch(**branch), Branch)

    created_at = datetime.fromisoformat(branch['created_at'])
    assert isinstance(created_at, datetime)


def test_get_branch_with_one_record(client, branch):
    response = client.get(f'/taxonomy/branch/{branch.taxonomy_id}/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_branches_with_multiple_records(client, create_branch):
    create_branch(title='Branch A')
    response = create_branch(title='Branch B')
    taxonomy_id = response.json()['taxonomy_id']

    response = client.get(f'/taxonomy/branch/{taxonomy_id}/')

    assert response.status_code == HTTPStatus.OK
    branches = response.json()
    assert len(branches) == 1

    returned_titles = {b['title'] for b in branches}
    assert returned_titles == {'Branch B'}


def test_get_branches_with_filter(client, create_branch):
    branch1 = create_branch(title='Branch A').json()
    _branch2 = create_branch(title='Branch B').json()
    taxonomy_id = branch1.get('taxonomy_id')

    response = client.get(f'/taxonomy/branch/{taxonomy_id}/')

    assert response.status_code == HTTPStatus.OK

    returned_id = {b['id'] for b in response.json()}
    assert returned_id == {branch1['id']}

    returned_titles = {b['title'] for b in response.json()}
    assert returned_titles == {branch1['title']}


def test_update_branch(client, branch):
    updated_data = {
        'id': str(branch.id),
        'title': 'Updated Title',
        'taxonomy_id': str(branch.taxonomy_id),
        'description': branch.description,
    }

    response = client.put('/taxonomy/branch/', json=updated_data)
    assert response.status_code == HTTPStatus.OK

    response = client.get(f'/taxonomy/branch/{branch.taxonomy_id}/')
    branches = response.json()

    assert len(branches) == 1
    assert branches[0]['title'] == 'Updated Title'


def test_delete_branch(client, branch):
    response = client.delete(f'/taxonomy/branch/{branch.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(f'/taxonomy/branch/{branch.taxonomy_id}/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
