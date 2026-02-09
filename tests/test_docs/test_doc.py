import uuid
from http import HTTPStatus
from uuid import uuid4

import pytest

from iaEditais.schemas import DocumentPublic


@pytest.mark.asyncio
async def test_create_doc(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/doc,
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
        '/doc,
        json={
            'name': 'Doc A',
            'description': 'Another desc',
            'identifier': 'DOC-001',
            'typification_ids': [],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail']
        == 'Doc with identifier "DOC-001" already exists.'
    )

    response = client.post(
        '/doc,
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
        == 'Doc with identifier "DOC-001" already exists.'
    )


def test_read_docs_empty(client):
    response = client.get('/doc)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'documents': []}


@pytest.mark.asyncio
async def test_read_docs_with_data(client, create_doc):
    doc = await create_doc(
        name='Doc X', description='Description X', identifier='DOC-X'
    )
    doc_schema = DocumentPublic.model_validate(doc).model_dump(mode='json')

    response = client.get('/doc)
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
        '/doc,
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
        '/doc,
        json={
            'id': str(doc_b.id),
            'name': 'Doc A',
            'description': 'Some desc',
            'identifier': 'ID-A',
            'typification_ids': [str(typ.id)],
            'editors_ids': [],
        },
    )
    assert response.status_code == HTTPStatus.CONFLICT
    assert (
        response.json()['detail']
        == 'Doc with identifier "ID-A" already exists.'
    )


@pytest.mark.asyncio
async def test_update_nonexistent_doc(logged_client):
    client, *_ = await logged_client()
    response = client.put(
        '/doc,
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
async def test_read_docs_archived_default_false_excludes_archived(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc A', identifier='DOC-A')
    archived_doc = await create_doc(name='Doc B', identifier='DOC-B')

    r = client.put(f'/doc/{archived_doc.id}/toggle-archive')
    assert r.status_code == HTTPStatus.OK

    response = client.get('/doc)
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert len(data['documents']) == 1
    assert data['documents'][0]['id'] == str(doc.id)


@pytest.mark.asyncio
async def test_read_docs_filter_archived_true_returns_only_archived(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    non_archived_1 = await create_doc(name='Doc A2', identifier='DOC-A2')
    archived = await create_doc(name='Doc A3', identifier='DOC-A3')
    non_archived_2 = await create_doc(name='Doc A4', identifier='DOC-A4')

    r = client.put(f'/doc/{archived.id}/toggle-archive')
    assert r.status_code == HTTPStatus.OK

    response = client.get('/doc/?archived=true')
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert len(data['documents']) == 1
    assert data['documents'][0]['id'] == str(archived.id)


@pytest.mark.asyncio
async def test_read_docs_filter_archived_false_returns_only_non_archived(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    non_archived_1 = await create_doc(name='Doc NA1', identifier='DOC-NA1')
    archived = await create_doc(name='Doc AR1', identifier='DOC-AR1')
    non_archived_2 = await create_doc(name='Doc NA2', identifier='DOC-NA2')

    r = client.put(f'/doc/{archived.id}/toggle-archive')
    assert r.status_code == HTTPStatus.OK

    response = client.get('/doc/?archived=false')
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    ids = [d['id'] for d in data['documents']]
    assert len(ids) == 2
    assert str(non_archived_1.id) in ids
    assert str(non_archived_2.id) in ids
    assert str(archived.id) not in ids


@pytest.mark.asyncio
async def test_toggle_archive_switches_value_and_persists(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc Toggle', identifier='DOC-T1')

    r0 = client.get(f'/doc/{doc.id}')
    assert r0.status_code == HTTPStatus.OK
    d0 = r0.json()
    assert 'is_archived' in d0
    assert d0['is_archived'] is False

    r1 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert r1.status_code == HTTPStatus.OK

    r2 = client.get(f'/doc/{doc.id}')
    assert r2.status_code == HTTPStatus.OK
    d2 = r2.json()
    assert d2['is_archived'] is True

    r3 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert r3.status_code == HTTPStatus.OK

    r4 = client.get(f'/doc/{doc.id}')
    assert r4.status_code == HTTPStatus.OK
    d4 = r4.json()
    assert d4['is_archived'] is False


@pytest.mark.asyncio
async def test_toggle_archive_not_found(logged_client):
    client, *_ = await logged_client()
    random_id = uuid4()
    response = client.put(f'/doc/{random_id}/toggle-archive')
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_read_doc_by_id_includes_is_archived_and_value(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc Check', identifier='DOC-CHECK')

    r0 = client.get(f'/doc/{doc.id}')
    assert r0.status_code == HTTPStatus.OK
    d0 = r0.json()
    assert 'is_archived' in d0
    assert d0['is_archived'] is False

    r1 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert r1.status_code == HTTPStatus.OK

    r2 = client.get(f'/doc/{doc.id}')
    assert r2.status_code == HTTPStatus.OK
    d2 = r2.json()
    assert 'is_archived' in d2
    assert d2['is_archived'] is True


@pytest.mark.asyncio
async def test_full_archive_flow_archive_and_unarchive_affects_filters(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    doc = await create_doc(name='Flow Doc', identifier='FLOW')

    r_default_0 = client.get('/doc)
    assert r_default_0.status_code == HTTPStatus.OK
    ids_default_0 = [d['id'] for d in r_default_0.json()['documents']]
    assert str(doc.id) in ids_default_0

    r_archived_true_0 = client.get('/doc/?archived=true')
    assert r_archived_true_0.status_code == HTTPStatus.OK
    ids_archived_true_0 = [
        d['id'] for d in r_archived_true_0.json()['documents']
    ]
    assert str(doc.id) not in ids_archived_true_0

    r_toggle_1 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert r_toggle_1.status_code == HTTPStatus.OK

    r_default_1 = client.get('/doc)
    assert r_default_1.status_code == HTTPStatus.OK
    ids_default_1 = [d['id'] for d in r_default_1.json()['documents']]
    assert str(doc.id) not in ids_default_1

    r_archived_true_1 = client.get('/doc/?archived=true')
    assert r_archived_true_1.status_code == HTTPStatus.OK
    ids_archived_true_1 = [
        d['id'] for d in r_archived_true_1.json()['documents']
    ]
    assert str(doc.id) in ids_archived_true_1

    r_archived_false_1 = client.get('/doc/?archived=false')
    assert r_archived_false_1.status_code == HTTPStatus.OK
    ids_archived_false_1 = [
        d['id'] for d in r_archived_false_1.json()['documents']
    ]
    assert str(doc.id) not in ids_archived_false_1

    r_toggle_2 = client.put(f'/doc/{doc.id}/toggle-archive')
    assert r_toggle_2.status_code == HTTPStatus.OK

    r_default_2 = client.get('/doc)
    assert r_default_2.status_code == HTTPStatus.OK
    ids_default_2 = [d['id'] for d in r_default_2.json()['documents']]
    assert str(doc.id) in ids_default_2

    r_archived_true_2 = client.get('/doc/?archived=true')
    assert r_archived_true_2.status_code == HTTPStatus.OK
    ids_archived_true_2 = [
        d['id'] for d in r_archived_true_2.json()['documents']
    ]
    assert str(doc.id) not in ids_archived_true_2

    r_archived_false_2 = client.get('/doc/?archived=false')
    assert r_archived_false_2.status_code == HTTPStatus.OK
    ids_archived_false_2 = [
        d['id'] for d in r_archived_false_2.json()['documents']
    ]
    assert str(doc.id) in ids_archived_false_2


@pytest.mark.asyncio
async def test_read_docs_archived_param_is_case_insensitive_truthy_values(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    archived = await create_doc(name='Doc AR2', identifier='DOC-AR2')
    r = client.put(f'/doc/{archived.id}/toggle-archive')
    assert r.status_code == HTTPStatus.OK

    for v in ['true', 'True', '1', 'on', 'yes']:
        response = client.get(f'/doc/?archived={v}')
        assert response.status_code == HTTPStatus.OK
        ids = [d['id'] for d in response.json()['documents']]
        assert str(archived.id) in ids


@pytest.mark.asyncio
async def test_read_docs_archived_param_is_case_insensitive_falsy_values(
    logged_client, create_doc
):
    client, *_ = await logged_client()
    non_archived = await create_doc(name='Doc NA3', identifier='DOC-NA3')
    archived = await create_doc(name='Doc AR3', identifier='DOC-AR3')
    r = client.put(f'/doc/{archived.id}/toggle-archive')
    assert r.status_code == HTTPStatus.OK

    for v in ['false', 'False', '0', 'off', 'no']:
        response = client.get(f'/doc/?archived={v}')
        assert response.status_code == HTTPStatus.OK
        ids = [d['id'] for d in response.json()['documents']]
        assert str(non_archived.id) in ids
        assert str(archived.id) not in ids
