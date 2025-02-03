from http import HTTPStatus
from iaEditais.schemas.Source import Source


def test_create_source(client):
    file_content = b'%PDF-1.4\n...fake pdf content...'
    files = {'file': ('testfile.pdf', file_content, 'application/pdf')}
    response = client.post('/source/', files=files)
    source = response.json()
    assert isinstance(Source(**source), Source)
    assert response.status_code == HTTPStatus.CREATED


def test_create_source_with_txt(client):
    file_content = b'text content'
    files = {'file': ('testfile.txt', file_content, 'text/plain')}
    response = client.post('/source/', files=files)
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_get_source_no_content(client):
    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    source = response.json()
    assert len(source) == 0


def test_get_source_with_one_record(client):
    file_content = b'%PDF-1.4\n...fake pdf content...'
    files = {'file': ('testfile1.pdf', file_content, 'application/pdf')}
    client.post('/source/', files=files)

    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    source = response.json()
    assert len(source) == 1


def test_get_source_with_two_records(client):
    file_content_1 = b'%PDF-1.4\n...fake pdf content 1...'
    files_1 = {'file': ('testfile1.pdf', file_content_1, 'application/pdf')}
    client.post('/source/', files=files_1)

    file_content_2 = b'%PDF-1.4\n...fake pdf content 2...'
    files_2 = {'file': ('testfile2.pdf', file_content_2, 'application/pdf')}
    client.post('/source/', files=files_2)

    response = client.get('/source/')
    assert response.status_code == HTTPStatus.OK
    source = response.json()
    assert len(source) == 2


def test_get_source_by_id(client):
    file_content = b'%PDF-1.4\n...fake pdf content...'
    files = {'file': ('testfile.pdf', file_content, 'application/pdf')}
    post_response = client.post('/source/', files=files)
    source = post_response.json()
    source_id = source['id']

    response = client.get(f'/source/{source_id}/')
    assert response.status_code == HTTPStatus.OK
    assert response.headers['Content-Type'] == 'application/pdf'


def test_delete_source_by_id(client):
    file_content = b'%PDF-1.4\n...fake pdf content...'
    files = {'file': ('testfile.pdf', file_content, 'application/pdf')}
    post_response = client.post('/source/', files=files)
    source = post_response.json()
    source_id = source['id']

    delete_response = client.delete(f'/source/{source_id}/')
    assert delete_response.status_code == HTTPStatus.NO_CONTENT

    get_response = client.get(f'/source/{source_id}/')
    assert get_response.status_code == HTTPStatus.NOT_FOUND
