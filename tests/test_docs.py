from http import HTTPStatus

import pytest

from iaEditais.models import doc as doc_model


@pytest.mark.asyncio
async def test_doc_post(client, create_typification):
    ty = await create_typification()
    id = str(ty.id)
    payload = {'name': 'doc', 'identifier': 'TEST-001','typification': [id]}
    response = client.post('/doc/', json=payload)
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
async def test_get_docs(client, create_doc):
    await create_doc()
    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_delete_doc(client, create_doc):
    doc = await create_doc()
    response = client.delete(f'/doc/{doc.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT
    response = client.get('/doc/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_post_release(client, create_doc):
    doc = await create_doc()
    doc_id = str(doc.id)

    path = 'tests/storage/sample.pdf'

    with open(path, 'rb') as f:
        file = {'file': (path, f, 'application/pdf')}
        response = client.post(f'/doc/{doc_id}/release/', files=file)

    assert response.status_code == HTTPStatus.CREATED
    assert doc_model.Release(**response.json())


@pytest.mark.asyncio
async def test_release_get(client, create_doc, create_release):
    doc = await create_doc()
    await create_release(doc)
    response = client.get(f'/doc/{doc.id}/release/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_release_delete(client, create_doc, create_release):
    doc = await create_doc()
    release = await create_release(doc)

    response = client.delete(f'/doc/{doc.id}/release/{release.id}/')
    assert response.status_code == HTTPStatus.NO_CONTENT

    response = client.get(f'/doc/{doc.id}/release/')
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 0


@pytest.mark.asyncio
async def test_get_release_file(client, create_doc, create_release):
    doc = await create_doc()
    release = await create_release(doc)

    response = client.get(f'/doc/{doc.id}/release/{release.id}/')

    assert response.status_code == HTTPStatus.OK
    assert response.headers['content-type'] == 'application/pdf'
    assert response.content
