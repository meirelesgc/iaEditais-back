from http import HTTPStatus
from uuid import uuid4
from iaEditais.schemas.Source import Source


def test_create_source(client, create_source):
    response = create_source()
    source = response.json()
    assert isinstance(Source(**source), Source)
    assert response.status_code == HTTPStatus.CREATED


def test_create_source_without_file(client, source_data_factory):
    source_data = source_data_factory()
    response = client.post('/source/', files={}, data=source_data['data'])
    assert response.status_code == HTTPStatus.CREATED


def test_create_duplicate_source(client, create_source):
    response = create_source(
        'Test CONFLICT Source',
        b'%PDF-1.4\n...fake pdf content 1...',
    )
    response = create_source(
        'Test CONFLICT Source',
        b'%PDF-1.4\n...fake pdf content 2...',
    )
    assert response.status_code == HTTPStatus.CONFLICT


def test_create_source_with_txt(client, source_data_factory):
    source_data = source_data_factory(file_content=b'text content')
    source_data['files']['file'] = (
        'testfile.txt',
        b'text content',
        'text/plain',
    )

    response = client.post(
        '/source/', files=source_data['files'], data=source_data['data']
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_get_source_no_content(client):
    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == []


def test_get_source_with_one_record(client, create_source):
    create_source()
    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


def test_get_source_with_two_records(client, create_source):
    create_source('Test Source 1', b'%PDF-1.4\n...fake pdf content 1...')
    create_source('Test Source 2', b'%PDF-1.4\n...fake pdf content 2...')

    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2


def test_get_source_by_id(client, create_source):
    post_response = create_source()
    source_id = post_response.json()['id']

    response = client.get(f'/source/{source_id}/')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/pdf'


def test_delete_source_by_id(client, create_source):
    post_response = create_source()
    source_id = post_response.json()['id']

    delete_response = client.delete(f'/source/{source_id}/')
    assert delete_response.status_code == HTTPStatus.NO_CONTENT

    get_response = client.get(f'/source/{source_id}/')
    assert get_response.status_code == HTTPStatus.NOT_FOUND


def test_delete_source_with_the_wrong_id(client, create_source):
    create_source()
    delete_response = client.delete(f'/source/{uuid4()}/')
    assert delete_response.status_code == HTTPStatus.NOT_FOUND
