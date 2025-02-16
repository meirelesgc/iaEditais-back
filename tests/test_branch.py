from http import HTTPStatus
from datetime import datetime
from iaEditais.schemas.Branch import Branch


def test_create_branch(client, taxonomy_payload, branch_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    branch_payload['taxonomy_id'] = response.json()['id']

    response = client.post('/taxonomy/branch/', json=branch_payload)

    assert response.status_code == HTTPStatus.CREATED
    assert isinstance(Branch(**response.json()), Branch)
    created_at = datetime.fromisoformat(response.json()['created_at'])
    assert isinstance(created_at, datetime)


def test_get_branch_with_one_record(client, taxonomy_payload, branch_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    branch_payload['taxonomy_id'] = response.json()['id']
    response = client.post('/taxonomy/branch/', json=branch_payload)

    response = client.get('/taxonomy/branch/')

    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_branches_with_multiple_records(
    client, taxonomy_payload, branch_payload
):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    branch_payload['taxonomy_id'] = response.json()['id']
    branches_payload = [branch_payload, branch_payload]

    for payload in branches_payload:
        client.post('/taxonomy/branch/', json=payload)

    response = client.get('/taxonomy/branch/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2


def test_get_branches_with_filter(client, taxonomy_payload, branch_payload):
    for _ in range(2):
        response = client.post('/taxonomy/', json=taxonomy_payload)
        branch_payload['taxonomy_id'] = response.json()['id']
        client.post('/taxonomy/branch/', json=branch_payload)

    response = client.get(f'/taxonomy/branch/{response.json()["id"]}/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_update_branch(client, taxonomy_payload, branch_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    branch_payload['taxonomy_id'] = response.json()['id']
    response = client.post('/taxonomy/branch/', json=branch_payload)

    branch_payload = response.json()
    branch_payload['title'] = 'Updated Title'

    client.put('/taxonomy/branch/', json=branch_payload)
    response = client.get('/taxonomy/branch/')

    assert response.status_code == HTTPStatus.OK
    assert {'Updated Title'} == {g['title'] for g in response.json()}


def test_delete_branch(client, taxonomy_payload, branch_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    branch_payload['taxonomy_id'] = response.json()['id']
    response = client.post('/taxonomy/branch/', json=branch_payload)

    response = client.delete(f'/taxonomy/branch/{response.json()["id"]}')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/taxonomy/branch/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
