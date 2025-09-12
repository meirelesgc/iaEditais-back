import uuid
from datetime import datetime, timezone
from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_set_status_pending(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc to be Pending', identifier='ST-001')

    response = client.put(f'/doc/{doc.id}/status/pending')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)
    assert data['status'] == 'pending'


@pytest.mark.asyncio
async def test_set_status_under_construction(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc for Construction', identifier='ST-002')

    response = client.put(f'/doc/{doc.id}/status/under-construction')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)
    assert data['status'] == 'under-construction'


@pytest.mark.asyncio
async def test_set_status_waiting_review(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc for Review', identifier='ST-003')

    response = client.put(f'/doc/{doc.id}/status/waiting-review')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)
    assert data['status'] == 'waiting-review'


@pytest.mark.asyncio
async def test_set_status_completed(logged_client, create_doc):
    client, *_ = await logged_client()
    doc = await create_doc(name='Doc to Complete', identifier='ST-004')

    response = client.put(f'/doc/{doc.id}/status/completed')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['id'] == str(doc.id)
    assert data['status'] == 'completed'


@pytest.mark.asyncio
async def test_set_status_for_nonexistent_doc(logged_client):
    client, *_ = await logged_client()
    nonexistent_id = uuid.uuid4()

    response = client.put(f'/doc/{nonexistent_id}/status/pending')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Doc not found'}


@pytest.mark.asyncio
async def test_set_status_on_deleted_doc(logged_client, create_doc, session):
    client, *_ = await logged_client()
    doc = await create_doc(name='Deleted Doc', identifier='DEL-999')

    doc.deleted_at = datetime.now(timezone.utc)
    session.add(doc)
    await session.commit()

    response = client.put(f'/doc/{doc.id}/status/pending')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Doc not found'}
