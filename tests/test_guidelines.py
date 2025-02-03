from http import HTTPStatus
import pytest
from iaEditais.schemas.Guideline import Guideline


@pytest.fixture
def guideline_payload():
    return {
        'title': 'Test Guideline',
        'description': 'This is a test guideline.',
        'source': [],
    }


def test_create_guideline(client, guideline_payload):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    assert response.status_code == HTTPStatus.CREATED

    guideline = response.json()
    assert isinstance(Guideline(**guideline), Guideline)
    assert guideline['title'] == guideline_payload['title']
    assert guideline['description'] == guideline_payload['description']


def test_get_guidelines_empty(client):
    response = client.get('/taxonomy/guideline/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_guidelines_with_one_record(client, guideline_payload):
    client.post('/taxonomy/guideline/', json=guideline_payload)

    response = client.get('/taxonomy/guideline/')
    assert response.status_code == HTTPStatus.OK

    guidelines = response.json()
    assert len(guidelines) == 1
    assert guidelines[0]['title'] == guideline_payload['title']


def test_get_guidelines_with_multiple_records(client, guideline_payload):
    guidelines_payloads = [guideline_payload, guideline_payload]

    for payload in guidelines_payloads:
        client.post('/taxonomy/guideline/', json=payload)

    response = client.get('/taxonomy/guideline/')
    assert response.status_code == HTTPStatus.OK

    guidelines = response.json()
    assert len(guidelines) == len(guidelines_payloads)
    returned_titles = {g['title'] for g in guidelines}
    expected_titles = {p['title'] for p in guidelines_payloads}
    assert returned_titles == expected_titles


def test_put_guideline(client, guideline_payload):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    assert response.status_code == HTTPStatus.CREATED

    updated_payload = response.json()
    updated_payload['title'] = 'Updated Title'

    response = client.put('/taxonomy/guideline/', json=updated_payload)
    assert response.status_code == HTTPStatus.OK

    response = client.get('/taxonomy/guideline/')
    guidelines = response.json()
    returned_titles = {g['title'] for g in guidelines}
    expected_titles = {'Updated Title'}

    assert returned_titles == expected_titles


def test_delete_guideline(client, guideline_payload):
    response = client.post('/taxonomy/guideline/', json=guideline_payload)
    assert response.status_code == HTTPStatus.CREATED

    guideline_id = response.json().get('id')

    response = client.delete(f'/taxonomy/guideline/{guideline_id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/taxonomy/guideline/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
