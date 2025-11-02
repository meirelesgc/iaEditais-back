import uuid
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_create_message_success(
    logged_client, create_doc, create_release, create_typification
):
    client, *_ = await logged_client()

    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='Doc with Message',
        identifier='MSG-001',
        typification_ids=[str(typ1.id)],
    )
    await create_release(doc)

    payload = {'content': 'This is a message content.'}

    response = client.post(f'/doc/{doc.id}/message', json=payload)
    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert 'id' in data
    assert data['content'] == 'This is a message content.'
    assert data['document_id'] == str(doc.id)


@pytest.mark.asyncio
async def test_create_message_document_not_found(logged_client):
    client, *_ = await logged_client()
    fake_doc_id = uuid.uuid4()

    response = client.post(
        f'/doc/{fake_doc_id}/message',
        json={'content': 'Message for non-existent document'},
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Document not found.'}


@pytest.mark.asyncio
async def test_list_messages_empty(
    logged_client, create_doc, create_typification
):
    client, *_ = await logged_client()
    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='Empty Msg Doc',
        identifier='MSG-002',
        typification_ids=[str(typ1.id)],
    )
    response = client.get(f'/doc/{doc.id}/messages')
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'messages': []}


@pytest.mark.asyncio
async def test_list_messages_with_results(
    logged_client,
    create_doc,
    create_release,
    create_message,
    create_typification,
    create_user,
):
    client, *_ = await logged_client()
    author = await create_user()

    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='List Msg Doc',
        identifier='MSG-003',
        typification_ids=[str(typ1.id)],
    )
    await create_release(doc)

    msg1 = await create_message(
        doc, content='First message', author_id=author.id
    )
    msg2 = await create_message(
        doc, content='Second message', author_id=author.id
    )

    response = client.get(f'/doc/{doc.id}/messages')
    assert response.status_code == HTTPStatus.OK
    data = response.json()

    assert len(data['messages']) == 2
    contents = [m['content'] for m in data['messages']]
    assert 'First message' in contents
    assert 'Second message' in contents


@pytest.mark.asyncio
async def test_list_messages_with_filters(
    logged_client,
    create_doc,
    create_release,
    create_message,
    create_typification,
    create_user,
):
    client, *_ = await logged_client()
    author = await create_user()

    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='Filter Msg Doc',
        identifier='MSG-004',
        typification_ids=[str(typ1.id)],
    )
    await create_release(doc)
    msg = await create_message(doc, content='Filter me', author_id=author.id)

    start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    end = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

    response = client.get(
        f'/doc/{doc.id}/messages',
        params={
            'author_id': msg.author_id,
            'start_date': start,
            'end_date': end,
        },
    )

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['messages']) == 1
    assert data['messages'][0]['id'] == str(msg.id)


@pytest.mark.asyncio
async def test_read_message_success(
    logged_client,
    create_doc,
    create_release,
    create_message,
    create_typification,
    create_user,
):
    client, *_ = await logged_client()
    author = await create_user()

    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='Doc Read Msg',
        identifier='MSG-005',
        typification_ids=[str(typ1.id)],
    )
    await create_release(doc)
    msg = await create_message(
        doc, content='Reading this message', author_id=author.id
    )

    response = client.get(f'/doc/message/{msg.id}')
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(msg.id)
    assert data['content'] == 'Reading this message'


@pytest.mark.asyncio
async def test_read_message_not_found(logged_client):
    client, *_ = await logged_client()
    fake_id = uuid.uuid4()

    response = client.get(f'/doc/message/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Message not found.'}


@pytest.mark.asyncio
async def test_update_message_success(
    logged_client,
    create_doc,
    create_release,
    create_message,
    create_typification,
    create_user,
):
    client, *_ = await logged_client()
    author = await create_user()

    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='Doc Update Msg',
        identifier='MSG-006',
        typification_ids=[str(typ1.id)],
    )
    await create_release(doc)
    msg = await create_message(
        doc, content='Original content', author_id=author.id
    )

    payload = {'id': str(msg.id), 'content': 'Updated content'}
    response = client.put('/doc/message', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['content'] == 'Updated content'
    assert data['updated_at'] is not None


@pytest.mark.asyncio
async def test_update_message_not_found(logged_client):
    client, *_ = await logged_client()
    fake_id = uuid.uuid4()
    payload = {'id': str(fake_id), 'content': 'No message here'}

    response = client.put('/doc/message', json=payload)
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Message not found.'}


@pytest.mark.asyncio
async def test_delete_message_success(
    logged_client,
    create_doc,
    create_release,
    create_message,
    create_typification,
    create_user,
):
    client, *_ = await logged_client()
    author = await create_user()

    typ1 = await create_typification(name='Typ 1')
    doc = await create_doc(
        name='Doc Delete Msg',
        identifier='MSG-007',
        typification_ids=[str(typ1.id)],
    )
    await create_release(doc)
    msg = await create_message(
        doc, content='To be deleted', author_id=author.id
    )

    response = client.delete(f'/doc/message/{msg.id}')
    assert response.status_code == HTTPStatus.NO_CONTENT

    list_response = client.get(f'/doc/{doc.id}/messages')
    assert list_response.status_code == HTTPStatus.OK
    assert list_response.json() == {'messages': []}


@pytest.mark.asyncio
async def test_delete_message_not_found(logged_client):
    client, *_ = await logged_client()
    fake_id = uuid.uuid4()

    response = client.delete(f'/doc/message/{fake_id}')
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Message not found.'}
