import uuid
from http import HTTPStatus

import pytest

from iaEditais.models import DocumentStatus


@pytest.mark.asyncio
async def test_create_document_message_success(logged_client, create_doc):
    client, token, auth_headers, user = await logged_client()
    doc = await create_doc(name='Doc With Message', identifier='MSG-001')

    response = client.post(
        f'/doc/{doc.id}/message',
        json={'message': 'Esta é uma mensagem de teste.'},
    )

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['message'] == 'Esta é uma mensagem de teste.'
    assert 'id' in data
    assert 'created_at' in data
    assert data['user']['id'] == str(user.id)
    assert data['user']['username'] == user.username


@pytest.mark.asyncio
async def test_create_message_for_nonexistent_doc(logged_client):
    client, *_ = await logged_client()
    non_existent_uuid = uuid.uuid4()

    response = client.post(
        f'/doc/{non_existent_uuid}/message',
        json={'message': 'Mensagem para um documento fantasma.'},
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Documento não encontrado.'}


@pytest.mark.asyncio
async def test_create_message_with_invalid_payload(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc Invalid Payload', identifier='INV-001')

    response = client.post(
        f'/doc/{doc.id}/message',
        json={'texto_errado': 'Isso não deveria funcionar'},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_message_unauthenticated(client, create_doc):
    doc = await create_doc(name='Doc Unauthenticated', identifier='AUTH-001')

    response = client.post(
        f'/doc/{doc.id}/message',
        json={'message': 'Tentativa sem login.'},
    )

    assert response.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_message_appears_in_document_history(logged_client, create_doc):
    client, token, auth_headers, user = await logged_client()
    doc = await create_doc(name='Doc To Receive Message', identifier='MSG-100')
    message_content = 'Esta é a primeira mensagem.'

    post_response = client.post(
        f'/doc/{doc.id}/message',
        json={'message': message_content},
    )
    assert post_response.status_code == HTTPStatus.CREATED

    get_response = client.get(f'/doc/{doc.id}')
    assert get_response.status_code == HTTPStatus.OK

    data = get_response.json()
    assert len(data['history']) == 1
    latest_history = data['history'][0]

    assert len(latest_history['messages']) == 1
    message_in_history = latest_history['messages'][0]

    assert message_in_history['message'] == message_content
    assert message_in_history['user']['id'] == str(user.id)


@pytest.mark.asyncio
async def test_message_stays_with_old_history_after_status_change(
    logged_client, create_doc
):
    client, token, auth_headers, user = await logged_client()
    doc = await create_doc(
        name='Doc With History Change', identifier='HIS-200'
    )
    original_message = 'Mensagem no histórico PENDENTE.'

    client.post(f'/doc/{doc.id}/message', json={'message': original_message})

    update_status_response = client.put(
        f'/doc/{doc.id}/status/under-construction'
    )
    assert update_status_response.status_code == HTTPStatus.OK

    get_response = client.get(f'/doc/{doc.id}')
    assert get_response.status_code == HTTPStatus.OK
    data = get_response.json()

    assert len(data['history']) == 2

    newest_history = data['history'][0]
    old_history = data['history'][1]

    assert newest_history['status'] == DocumentStatus.UNDER_CONSTRUCTION.value
    assert len(newest_history['messages']) == 0

    assert old_history['status'] == DocumentStatus.PENDING.value
    assert len(old_history['messages']) == 1
    assert old_history['messages'][0]['message'] == original_message
