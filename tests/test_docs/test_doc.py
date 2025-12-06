import uuid
from http import HTTPStatus
from uuid import uuid4

import pytest

from iaEditais.schemas import DocumentPublic


@pytest.mark.asyncio
async def test_create_doc(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/doc/',
        json={
            'name': 'New Doc',
            'description': 'A doc description',
            'identifier': 'DOC-123',
            'typification_ids': [],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'New Doc'
    assert data['description'] == 'A doc description'
    assert data['identifier'] == 'DOC-123'
    assert 'id' in data


@pytest.mark.asyncio
async def test_create_doc_conflict(logged_client, create_doc):
    client, *_ = await logged_client()
    await create_doc(name='Doc A', identifier='DOC-001')
    response = client.post(
        '/doc/',
        json={
            'name': 'Doc A',
            'description': 'Another desc',
            'identifier': 'DOC-002',
            'typification_ids': [],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail']
        == 'Doc with name "Doc A" or identifier "DOC-002" already exists.'
    )

    response = client.post(
        '/doc/',
        json={
            'name': 'Doc B',
            'description': 'Another desc',
            'identifier': 'DOC-001',
            'typification_ids': [],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail']
        == 'Doc with name "Doc B" or identifier "DOC-001" already exists.'
    )


def test_read_docs_empty(client):
    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'documents': []}


@pytest.mark.asyncio
async def test_read_docs_with_data(client, create_doc):
    doc = await create_doc(
        name='Doc X', description='Description X', identifier='DOC-X'
    )
    doc_schema = DocumentPublic.model_validate(doc).model_dump(mode='json')

    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'documents': [doc_schema]}


@pytest.mark.asyncio
async def test_read_doc_by_id(client, create_doc):
    doc = await create_doc(name='Doc Specific', identifier='DOC-999')

    response = client.get(f'/doc/{doc.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)
    assert data['name'] == 'Doc Specific'


def test_read_nonexistent_doc(client):
    response = client.get(f'/doc/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Doc not found'}


@pytest.mark.asyncio
async def test_update_doc(logged_client, create_doc, create_typification):
    client, *_ = await logged_client()
    doc = await create_doc(
        name='Doc Old', description='Old Desc', identifier='OLD-001'
    )

    typ1 = await create_typification(name='Typ 1')
    typ2 = await create_typification(name='Typ 2')

    response = client.put(
        '/doc/',
        json={
            'id': str(doc.id),
            'name': 'Doc Updated',
            'description': 'Updated Desc',
            'identifier': 'NEW-001',
            'typification_ids': [str(typ1.id), str(typ2.id)],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)
    assert data['name'] == 'Doc Updated'
    assert data['description'] == 'Updated Desc'
    assert data['identifier'] == 'NEW-001'
    typ_ids = [str(t['id']) for t in data.get('typifications', [])]
    assert set(typ_ids) == {str(typ1.id), str(typ2.id)}


@pytest.mark.asyncio
async def test_update_doc_conflict(
    logged_client, create_doc, create_typification
):
    client, *_ = await logged_client()
    await create_doc(name='Doc A', identifier='ID-A')
    doc_b = await create_doc(name='Doc B', identifier='ID-B')

    typ = await create_typification(name='Typ C')

    response = client.put(
        '/doc/',
        json={
            'id': str(doc_b.id),
            'name': 'Doc A',
            'description': 'Some desc',
            'identifier': 'ID-B',
            'typification_ids': [str(typ.id)],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail']
        == 'Doc with name "Doc A" or identifier "ID-B" already exists.'
    )

    response = client.put(
        '/doc/',
        json={
            'id': str(doc_b.id),
            'name': 'Doc B',
            'description': 'Some desc',
            'identifier': 'ID-A',
            'typification_ids': [str(typ.id)],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail']
        == 'Doc with name "Doc B" or identifier "ID-A" already exists.'
    )


@pytest.mark.asyncio
async def test_update_nonexistent_doc(logged_client):
    client, *_ = await logged_client()
    response = client.put(
        '/doc/',
        json={
            'id': str(uuid.uuid4()),
            'name': 'Ghost Doc',
            'description': '...',
            'identifier': 'GHOST-001',
            'typification_ids': [],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Doc not found'}


@pytest.mark.asyncio
async def test_delete_doc(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc Delete', identifier='DEL-001')

    delete_response = client.delete(f'/doc/{doc.id}')
    assert delete_response.status_code == HTTPStatus.NO_CONTENT

    get_response = client.get(f'/doc/{doc.id}')
    assert get_response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_nonexistent_doc(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/doc/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Doc not found'}


@pytest.mark.asyncio
async def test_read_docs_archived_default_false(client, create_doc):
    doc = await create_doc(name='Doc A', identifier='DOC-A')
    archived_doc = await create_doc(name='Doc B', identifier='DOC-B')
    client.put(f'/doc/{archived_doc.id}/toggle-archive')

    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['documents']) == 1
    assert data['documents'][0]['id'] == str(doc.id)


@pytest.mark.asyncio
async def test_read_docs_filter_archived_true(client, create_doc):
    doc = await create_doc(name='Doc A2', identifier='DOC-A2')
    archived = await create_doc(name='Doc A3', identifier='DOC-A3')
    client.put(f'/doc/{archived.id}/toggle-archive')
    non_archived = await create_doc(name='Doc A4', identifier='DOC-A4')

    response = client.get('/doc/?archived=true')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['documents']) == 1
    assert data['documents'][0]['id'] == str(archived.id)


@pytest.mark.asyncio
async def test_toggle_archive_switches_value(client, create_doc):
    doc = await create_doc(name='Doc Toggle', identifier='DOC-T1')

    response = client.put(f'/doc/{doc.id}/toggle-archive')
    assert response.status_code == HTTPStatus.OK

    response2 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert response2.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_toggle_archive_not_found(client):
    random_id = uuid4()
    response = client.put(f'/doc/{random_id}/toggle-archive')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_read_doc_by_id_includes_is_archived(client, create_doc):
    doc = await create_doc(name='Doc Check', identifier='DOC-CHECK')
    client.put(f'/doc/{doc.id}/toggle-archive')

    response = client.get(f'/doc/{doc.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)


@pytest.mark.asyncio
async def test_full_archive_flow(client, create_doc):
    doc = await create_doc(name='Flow Doc', identifier='FLOW')

    response = client.put(f'/doc/{doc.id}/toggle-archive')
    assert response.status_code == HTTPStatus.OK

    response2 = client.get('/doc/?archived=true')
    assert response2.status_code == HTTPStatus.OK
    data = response2.json()
    assert len(data['documents']) == 1
    assert data['documents'][0]['id'] == str(doc.id)

    response3 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert response3.status_code == HTTPStatus.OK
