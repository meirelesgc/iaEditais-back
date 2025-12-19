from uuid import uuid4

import pytest


def test_websocket_connection_and_broadcast(client):
    subscriber_id = str(uuid4())
    channel_id = 'ws:broadcast'
    message = f'User {subscriber_id} connected to channel - {channel_id}'
    with client.websocket_connect(f'/ws/{subscriber_id}') as websocket:
        data = websocket.receive_json()
        assert data['event'] == 'user.connect'
        assert data['message'] == message


@pytest.mark.asyncio
async def test_websocket_echo_broadcast(client):
    subscriber_id = str(uuid4())
    test_payload = 'Olá, esta é uma mensagem de teste'

    with client.websocket_connect(f'/ws/{subscriber_id}') as websocket:
        websocket.receive_text()
        websocket.send_text(test_payload)
        response = websocket.receive_json()
        assert response['event'] == 'user.connect'
        assert response['message'] == test_payload


@pytest.mark.asyncio
async def test_websocket_multiple_users_broadcast(client):
    user1_id = str(uuid4())
    user2_id = str(uuid4())

    with client.websocket_connect(f'/ws/{user1_id}') as ws1:
        ws1.receive_text()
        with client.websocket_connect(f'/ws/{user2_id}') as ws2:
            ws2.receive_text()
            msg_for_user1 = ws1.receive_json()
            assert f'User {user2_id} connected' in msg_for_user1['message']
            ws2.send_text('Mensagem do User 2')
            msg_recebida_user1 = ws1.receive_json()
            assert msg_recebida_user1['message'] == 'Mensagem do User 2'


@pytest.mark.asyncio
async def test_websocket_disconnect_broadcast(client):
    user_staying = str(uuid4())
    user_leaving = str(uuid4())

    with client.websocket_connect(f'/ws/{user_staying}') as ws_monitor:
        ws_monitor.receive_text()

        with client.websocket_connect(f'/ws/{user_leaving}'):
            ws_monitor.receive_text()

        msg_exit = ws_monitor.receive_json()
        assert 'disconnected to channel' in msg_exit['message']
        assert user_leaving in msg_exit['message']
