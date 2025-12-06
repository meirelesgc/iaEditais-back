import uuid
from datetime import datetime
from http import HTTPStatus

import pytest

from iaEditais.models import AuditLog


async def create_audit_log(session, user, **kwargs):
    log = AuditLog(
        table_name=kwargs.get('table_name', 'users'),
        record_id=kwargs.get('record_id', uuid.uuid4()),
        action=kwargs.get('action', 'CREATE'),
        user_id=user.id,
        old_data=kwargs.get('old_data', None),
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    await session.refresh(log, attribute_names=['user'])
    return log


@pytest.mark.asyncio
async def test_read_audit_logs_empty(logged_client):
    client, *_ = await logged_client()
    response = client.get('/audit-log/')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'audit_logs': []}


@pytest.mark.asyncio
async def test_read_audit_logs_basic_list(logged_client, session):
    client, _, _, user = await logged_client()

    log1 = await create_audit_log(
        session, user, action='CREATE', table_name='units'
    )
    log2 = await create_audit_log(
        session, user, action='UPDATE', table_name='documents'
    )

    response = client.get('/audit-log/')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['audit_logs']) == 2

    returned_ids = [log['id'] for log in data['audit_logs']]
    assert str(log1.id) in returned_ids
    assert str(log2.id) in returned_ids


@pytest.mark.asyncio
async def test_read_audit_logs_filter_by_table_name(logged_client, session):
    client, _, _, user = await logged_client()

    await create_audit_log(session, user, table_name='target_table')
    await create_audit_log(session, user, table_name='other_table')

    response = client.get('/audit-log/', params={'table_name': 'target'})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['audit_logs']) == 1
    assert data['audit_logs'][0]['table_name'] == 'target_table'


@pytest.mark.asyncio
async def test_read_audit_logs_filter_by_action(logged_client, session):
    client, _, _, user = await logged_client()

    await create_audit_log(session, user, action='DELETE')
    await create_audit_log(session, user, action='UPDATE')

    response = client.get('/audit-log/', params={'action': 'DELETE'})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['audit_logs']) == 1
    assert data['audit_logs'][0]['action'] == 'DELETE'


@pytest.mark.asyncio
async def test_read_audit_logs_filter_by_record_id(logged_client, session):
    client, _, _, user = await logged_client()

    target_id = uuid.uuid4()
    await create_audit_log(session, user, record_id=target_id)
    await create_audit_log(session, user, record_id=uuid.uuid4())

    response = client.get('/audit-log/', params={'record_id': str(target_id)})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['audit_logs']) == 1
    assert data['audit_logs'][0]['record_id'] == str(target_id)


@pytest.mark.asyncio
async def test_read_audit_logs_filter_by_user_id(
    logged_client, create_user, session
):
    client, _, _, user1 = await logged_client()
    user2 = await create_user(username='otheruser')

    await create_audit_log(session, user1, action='U1_ACTION')
    await create_audit_log(session, user2, action='U2_ACTION')

    response = client.get('/audit-log/', params={'user_id': str(user1.id)})

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['audit_logs']) == 1
    assert data['audit_logs'][0]['user_id'] == str(user1.id)


@pytest.mark.asyncio
async def test_read_audit_logs_date_filter(
    logged_client, session, mock_db_time
):
    client, _, _, user = await logged_client()

    date_past = datetime(2023, 1, 1, 12, 0, 0)
    date_future = datetime(2025, 1, 1, 12, 0, 0)

    with mock_db_time(model=AuditLog, time=date_past):
        log_past = await create_audit_log(session, user, action='PAST')

    with mock_db_time(model=AuditLog, time=date_future):
        log_future = await create_audit_log(session, user, action='FUTURE')

    response = client.get(
        '/audit-log/', params={'created_from': '2024-01-01T00:00:00'}
    )
    data = response.json()
    assert len(data['audit_logs']) == 1
    assert data['audit_logs'][0]['id'] == str(log_future.id)

    response = client.get(
        '/audit-log/', params={'created_to': '2024-01-01T00:00:00'}
    )
    data = response.json()
    assert len(data['audit_logs']) == 1
    assert data['audit_logs'][0]['id'] == str(log_past.id)


@pytest.mark.asyncio
async def test_read_audit_logs_pagination(logged_client, session):
    client, _, _, user = await logged_client()

    for i in range(15):
        await create_audit_log(session, user, action=f'ACTION_{i}')

    response = client.get('/audit-log/', params={'limit': 10, 'offset': 0})
    data = response.json()
    assert len(data['audit_logs']) == 10

    response = client.get('/audit-log/', params={'limit': 10, 'offset': 10})
    data = response.json()
    assert len(data['audit_logs']) == 5


@pytest.mark.asyncio
async def test_read_audit_logs_ordering(logged_client, session, mock_db_time):
    client, _, _, user = await logged_client()

    t1 = datetime(2024, 1, 1, 10, 0, 0)
    t2 = datetime(2024, 1, 1, 11, 0, 0)

    with mock_db_time(model=AuditLog, time=t1):
        log_old = await create_audit_log(session, user, action='OLD')

    with mock_db_time(model=AuditLog, time=t2):
        log_new = await create_audit_log(session, user, action='NEW')

    response = client.get('/audit-log/', params={'order': 'desc'})
    data = response.json()
    assert data['audit_logs'][0]['id'] == str(log_new.id)
    assert data['audit_logs'][1]['id'] == str(log_old.id)

    response = client.get('/audit-log/', params={'order': 'asc'})
    data = response.json()
    assert data['audit_logs'][0]['id'] == str(log_old.id)
    assert data['audit_logs'][1]['id'] == str(log_new.id)
