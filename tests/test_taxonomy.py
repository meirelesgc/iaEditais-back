from http import HTTPStatus
from iaEditais.schemas.Taxonomy import Taxonomy


def test_create_taxonomy(client, taxonomy_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    assert response.status_code == HTTPStatus.CREATED

    taxonomy = response.json()
    assert isinstance(Taxonomy(**taxonomy), Taxonomy)


def test_get_taxonomies_empty(client):
    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_taxonomies_with_one_record(client, taxonomy_payload):
    client.post('/taxonomy/', json=taxonomy_payload)

    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK

    taxonomies = response.json()
    assert len(taxonomies) == 1
    assert taxonomies[0]['title'] == taxonomy_payload['title']


def test_get_taxonomies_with_multiple_records(client, taxonomy_payload):
    taxonomies_payloads = [taxonomy_payload, taxonomy_payload]

    for payload in taxonomies_payloads:
        client.post('/taxonomy/', json=payload)

    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK

    taxonomies = response.json()
    assert len(taxonomies) == len(taxonomies_payloads)
    returned_titles = {g['title'] for g in taxonomies}
    expected_titles = {p['title'] for p in taxonomies_payloads}
    assert returned_titles == expected_titles


def test_put_taxonomy(client, taxonomy_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    assert response.status_code == HTTPStatus.CREATED

    updated_payload = response.json()
    updated_payload['title'] = 'Updated Title'

    response = client.put('/taxonomy/', json=updated_payload)
    assert response.status_code == HTTPStatus.OK

    response = client.get('/taxonomy/')
    taxonomies = response.json()
    returned_titles = {g['title'] for g in taxonomies}
    expected_titles = {'Updated Title'}

    assert returned_titles == expected_titles


def test_delete_taxonomies(client, taxonomy_payload):
    response = client.post('/taxonomy/', json=taxonomy_payload)
    assert response.status_code == HTTPStatus.CREATED

    taxonomy_id = response.json().get('id')

    response = client.delete(f'/taxonomy/{taxonomy_id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
