from http import HTTPStatus

from iaEditais.schemas.taxonomy import Taxonomy


def test_create_taxonomy(client, create_taxonomy):
    response = create_taxonomy()
    assert response.status_code == HTTPStatus.CREATED

    taxonomy = response.json()
    assert isinstance(Taxonomy(**taxonomy), Taxonomy)


def test_get_taxonomies_empty(client):
    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_taxonomies_with_one_record(client, taxonomy):
    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK

    taxonomies = response.json()
    assert len(taxonomies) == 1
    assert taxonomies[0]['title'] == taxonomy.title


def test_get_taxonomies_with_multiple_records(client, create_taxonomy):
    titles = ['Taxonomy A', 'Taxonomy B']

    for title in titles:
        create_taxonomy(title)

    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK

    taxonomies = response.json()
    assert len(taxonomies) == len(titles)

    returned_titles = {t['title'] for t in taxonomies}
    assert returned_titles == set(titles)


def test_put_taxonomy(client, taxonomy):
    updated_data = {
        'typification_id': str(taxonomy.typification_id),
        'id': str(taxonomy.id),
        'title': 'Updated Title',
        'description': 'Updated Description',
    }

    response = client.put('/taxonomy/', json=updated_data)
    assert response.status_code == HTTPStatus.OK

    response = client.get('/taxonomy/')
    taxonomies = response.json()
    returned_titles = {t['title'] for t in taxonomies}

    assert returned_titles == {'Updated Title'}


def test_delete_taxonomies(client, taxonomy):
    response = client.delete(f'/taxonomy/{taxonomy.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get('/taxonomy/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
