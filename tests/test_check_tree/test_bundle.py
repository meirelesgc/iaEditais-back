import uuid
from http import HTTPStatus

import pytest

from iaEditais.schemas.bundle import BundlePublic


@pytest.mark.asyncio
async def test_create_bundle(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        '/bundle',
        json={
            'name': 'Bundle 1',
            'documents': [{'name': 'Doc 1', 'typification_ids': []}],
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['name'] == 'Bundle 1'
    assert len(data['documents']) == 1
    assert data['documents'][0]['name'] == 'Doc 1'


@pytest.mark.asyncio
async def test_create_bundle_conflict(logged_client, create_bundle):
    client, *_ = await logged_client()
    await create_bundle(name='Bundle Existente')

    response = client.post(
        '/bundle',
        json={'name': 'Bundle Existente', 'documents': []},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Bundle name already exists'}


def test_read_bundles_empty(client):
    response = client.get('/bundle')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'bundles': []}


@pytest.mark.asyncio
async def test_read_bundles_with_data(client, create_bundle):
    bundle = await create_bundle(name='Bundle A')
    bundle_schema = BundlePublic.model_validate(bundle).model_dump(mode='json')

    response = client.get('/bundle')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'bundles': [bundle_schema]}


@pytest.mark.asyncio
async def test_read_bundle_by_id(client, create_bundle):
    bundle = await create_bundle(name='Bundle Especifico')
    response = client.get(f'/bundle/{bundle.id}')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(bundle.id)
    assert data['name'] == 'Bundle Especifico'


def test_read_nonexistent_bundle(client):
    response = client.get(f'/bundle/{uuid.uuid4()}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle not found'}


@pytest.mark.asyncio
async def test_update_bundle(logged_client, create_bundle):
    client, *_ = await logged_client()
    bundle = await create_bundle(name='Nome Antigo')

    response = client.put(
        '/bundle',
        json={'id': str(bundle.id), 'name': 'Nome Novo'},
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(bundle.id)
    assert data['name'] == 'Nome Novo'


@pytest.mark.asyncio
async def test_update_bundle_conflict(logged_client, create_bundle):
    client, *_ = await logged_client()
    await create_bundle(name='Bundle A')
    bundle_b = await create_bundle(name='Bundle B')

    response = client.put(
        '/bundle',
        json={'id': str(bundle_b.id), 'name': 'Bundle A'},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {'detail': 'Bundle name already exists'}


@pytest.mark.asyncio
async def test_update_nonexistent_bundle(logged_client):
    client, *_ = await logged_client()
    response = client.put(
        '/bundle',
        json={'id': str(uuid.uuid4()), 'name': 'Fantasma'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle not found'}


@pytest.mark.asyncio
async def test_delete_bundle(logged_client, create_bundle):
    client, *_ = await logged_client()
    bundle = await create_bundle(name='Deletar')

    response = client.delete(f'/bundle/{bundle.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_delete_nonexistent_bundle(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/bundle/{uuid.uuid4()}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle not found'}


@pytest.mark.asyncio
async def test_add_bundle_document(logged_client, create_bundle):
    client, *_ = await logged_client()
    bundle = await create_bundle()

    response = client.post(
        f'/bundle/{bundle.id}/document',
        json={'name': 'Novo Documento', 'typification_ids': []},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert len(data['documents']) == 1
    assert data['documents'][0]['name'] == 'Novo Documento'


@pytest.mark.asyncio
async def test_remove_bundle_document(
    logged_client, create_bundle, create_bundle_document
):
    client, *_ = await logged_client()
    bundle = await create_bundle()
    doc = await create_bundle_document(bundle_id=bundle.id)

    response = client.delete(f'/bundle/{bundle.id}/document/{doc.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_add_bundle_document_nonexistent_bundle(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        f'/bundle/{uuid.uuid4()}/document',
        json={'name': 'Doc', 'typification_ids': []},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle not found'}


@pytest.mark.asyncio
async def test_remove_bundle_document_nonexistent_bundle(logged_client):
    client, *_ = await logged_client()
    response = client.delete(f'/bundle/{uuid.uuid4()}/document/{uuid.uuid4()}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle not found'}


@pytest.mark.asyncio
async def test_create_bundle_with_valid_typifications(
    logged_client, create_typification
):
    client, *_ = await logged_client()
    typification = await create_typification()

    response = client.post(
        '/bundle',
        json={
            'name': 'Bundle Valid Typ',
            'documents': [
                {
                    'name': 'Doc 1',
                    'typification_ids': [str(typification.id)],
                }
            ],
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert len(data['documents'][0]['typifications']) == 1
    assert data['documents'][0]['typifications'][0]['id'] == str(
        typification.id
    )


@pytest.mark.asyncio
async def test_create_bundle_with_invalid_typifications(logged_client):
    client, *_ = await logged_client()

    response = client.post(
        '/bundle',
        json={
            'name': 'Bundle Invalid Typ',
            'documents': [
                {
                    'name': 'Doc 1',
                    'typification_ids': [str(uuid.uuid4())],
                }
            ],
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'One or more typifications not found'}


@pytest.mark.asyncio
async def test_add_bundle_document_with_valid_typifications(
    logged_client, create_bundle, create_typification
):
    client, *_ = await logged_client()
    bundle = await create_bundle()
    typification = await create_typification()

    response = client.post(
        f'/bundle/{bundle.id}/document',
        json={
            'name': 'Doc with Typ',
            'typification_ids': [str(typification.id)],
        },
    )

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.asyncio
async def test_add_bundle_document_with_invalid_typifications(
    logged_client, create_bundle
):
    client, *_ = await logged_client()
    bundle = await create_bundle()

    response = client.post(
        f'/bundle/{bundle.id}/document',
        json={
            'name': 'Doc invalid Typ',
            'typification_ids': [str(uuid.uuid4())],
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'One or more typifications not found'}


@pytest.mark.asyncio
async def test_remove_nonexistent_bundle_document(
    logged_client, create_bundle
):
    client, *_ = await logged_client()
    bundle = await create_bundle()

    response = client.delete(f'/bundle/{bundle.id}/document/{uuid.uuid4()}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle document not found'}


@pytest.mark.asyncio
async def test_remove_document_from_wrong_bundle(
    logged_client, create_bundle, create_bundle_document
):
    client, *_ = await logged_client()
    bundle_1 = await create_bundle()
    bundle_2 = await create_bundle()
    doc_bundle_1 = await create_bundle_document(bundle_id=bundle_1.id)

    response = client.delete(
        f'/bundle/{bundle_2.id}/document/{doc_bundle_1.id}'
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle document not found'}


@pytest.mark.asyncio
async def test_generate_bundle_documents_success(logged_client, create_bundle):
    client, *_ = await logged_client()
    bundle = await create_bundle()

    client.post(
        f'/bundle/{bundle.id}/document',
        json={'name': 'Edital', 'typification_ids': []},
    )
    client.post(
        f'/bundle/{bundle.id}/document',
        json={'name': 'Termo', 'typification_ids': []},
    )

    response = client.post(
        f'/bundle/{bundle.id}/generate-documents',
        json={
            'base_name': 'Expansao da rodovia',
            'base_identifier': 'EXP',
            'base_description': 'Descricao padrao',
        },
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert len(data) == 2

    names = [d['name'] for d in data]
    assert 'Edital - Expansao da rodovia' in names
    assert 'Termo - Expansao da rodovia' in names

    identifiers = [d['identifier'] for d in data]
    assert 'EXP-EDITAL' in identifiers
    assert 'EXP-TERMO' in identifiers


@pytest.mark.asyncio
async def test_generate_bundle_documents_not_found(logged_client):
    client, *_ = await logged_client()
    response = client.post(
        f'/bundle/{uuid.uuid4()}/generate-documents',
        json={
            'base_name': 'Expansao da rodovia',
            'base_identifier': 'EXP',
            'base_description': 'Descricao padrao',
        },
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Bundle not found.'}


@pytest.mark.asyncio
async def test_generate_bundle_documents_conflict(
    logged_client, create_bundle, create_doc
):
    client, *_ = await logged_client()
    bundle = await create_bundle()

    client.post(
        f'/bundle/{bundle.id}/document',
        json={'name': 'Edital', 'typification_ids': []},
    )

    await create_doc(name='Documento Existente', identifier='EXP-EDITAL')

    response = client.post(
        f'/bundle/{bundle.id}/generate-documents',
        json={
            'base_name': 'Expansao da rodovia',
            'base_identifier': 'EXP',
            'base_description': 'Descricao padrao',
        },
    )

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'Doc with identifier "EXP-EDITAL" already exists.'
    }
