import io
import uuid
from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_create_release(
    logged_client,
    create_doc,
    create_source,
    create_typification,
    create_taxonomy,
    create_branch,
):
    sources = await create_source(), await create_source()
    typification = await create_typification(
        source_ids=[s.id for s in sources]
    )
    taxonomy = await create_taxonomy(typification_id=typification.id)
    await create_branch(taxonomy_id=taxonomy.id)
    await create_branch(taxonomy_id=taxonomy.id)
    client, *_ = await logged_client()
    doc = await create_doc(
        name='Doc for Release',
        identifier='REL-001',
        typification_ids=[typification.id],
    )

    file_content = b'Este eh um arquivo de teste.'
    file = {'file': ('test_release.txt', io.BytesIO(file_content))}

    response = client.post(f'/doc/{doc.id}/release', files=file)

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert 'id' in data
    assert 'file_path' in data
    assert data['file_path'].endswith('.txt')

    # WIP - Voltar pra testar se salvou o arquivo no lugar certo


@pytest.mark.asyncio
async def test_create_release_doc_not_found(logged_client):
    client, *_ = await logged_client()
    non_existent_doc_id = uuid.uuid4()
    file_to_upload = {'file': ('ghost.txt', io.BytesIO(b'ghost file'))}

    response = client.post(
        f'/doc/{non_existent_doc_id}/release',
        files=file_to_upload,
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Document not found'}


@pytest.mark.asyncio
async def test_read_releases(
    logged_client, create_doc, create_release, create_typification
):
    client, *_ = await logged_client()
    typ1 = await create_typification(name='Typ 1')
    typ2 = await create_typification(name='Typ 2')

    doc = await create_doc(
        typification_ids=[str(typ1.id), str(typ2.id)],
        name='Doc with Files',
        identifier='REL-002',
    )

    response = client.get(f'/doc/{doc.id}/release')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'releases': []}

    await create_release(doc)

    response = client.get(f'/doc/{doc.id}/release')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['releases']) == 1
    assert 'id' in data['releases'][0]
    assert data['releases'][0]['file_path'].endswith('.txt')


@pytest.mark.asyncio
async def test_delete_release(logged_client, create_doc, create_typification):
    client, *_ = await logged_client()
    typification = await create_typification()
    doc = await create_doc(
        name='Doc to Delete From',
        identifier='REL-003',
        typification_ids=[typification.id],
    )

    upload_response = client.post(
        f'/doc/{doc.id}/release',
        files={'file': ('deletable.txt', io.BytesIO(b'to be deleted'))},
    )

    release_id = upload_response.json()['id']

    delete_response = client.delete(f'/doc/{doc.id}/release/{release_id}')
    assert delete_response.status_code == HTTPStatus.NO_CONTENT

    list_response = client.get(f'/doc/{doc.id}/release')
    assert list_response.status_code == HTTPStatus.OK
    assert list_response.json() == {'releases': []}


@pytest.mark.asyncio
async def test_delete_nonexistent_release(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc Test Delete', identifier='REL-004')
    non_existent_release_id = uuid.uuid4()

    response = client.delete(
        f'/doc/{doc.id}/release/{non_existent_release_id}'
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        'detail': 'File not found or does not belong to this document.'
    }


@pytest.mark.asyncio
async def test_delete_release_from_wrong_doc(
    logged_client, create_doc, create_typification
):
    client, *_ = await logged_client()
    typification = await create_typification()
    doc_a = await create_doc(
        name='Doc A',
        identifier='REL-A',
        typification_ids=[typification.id],
    )
    doc_b = await create_doc(
        name='Doc B',
        identifier='REL-B',
        typification_ids=[typification.id],
    )

    upload_response = client.post(
        f'/doc/{doc_a.id}/release',
        files={'file': ('file_a.txt', io.BytesIO(b'file from doc a'))},
    )
    release_a_id = upload_response.json()['id']

    response = client.delete(f'/doc/{doc_b.id}/release/{release_a_id}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {
        'detail': 'File not found or does not belong to this document.'
    }
