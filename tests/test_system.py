from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_create_system_setting(logged_client):
    client, *_ = await logged_client()
    payload = {
        'key': 'THEME_COLOR',
        'value': 'dark',
        'description': 'Cor do tema principal',
    }

    response = client.post('/system-settings', json=payload)

    assert response.status_code == HTTPStatus.CREATED
    data = response.json()
    assert data['key'] == 'THEME_COLOR'
    assert data['value'] == 'dark'
    assert data['description'] == 'Cor do tema principal'


@pytest.mark.asyncio
async def test_create_system_setting_conflict(
    logged_client, create_system_setting
):
    client, *_ = await logged_client()
    await create_system_setting(key='SITE_NAME', value='Meu Site')

    payload = {'key': 'SITE_NAME', 'value': 'Outro Site'}

    response = client.post('/system-settings', json=payload)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == {
        'detail': 'A setting with this key already exists'
    }


@pytest.mark.asyncio
async def test_create_system_setting_reactivate_deleted(
    logged_client, create_system_setting, session
):
    client, *_ = await logged_client()
    # Cria e deleta logicamente a configuração
    setting = await create_system_setting(
        key='TO_REACTIVATE', value='old_value'
    )
    response_delete = client.delete(f'/system-settings/{setting.key}')
    assert response_delete.status_code == HTTPStatus.OK

    # Tenta criar com a mesma chave
    payload = {'key': 'TO_REACTIVATE', 'value': 'new_value'}
    response_create = client.post('/system-settings', json=payload)

    assert response_create.status_code == HTTPStatus.CREATED
    data = response_create.json()
    assert data['key'] == 'TO_REACTIVATE'
    assert data['value'] == 'new_value'


@pytest.mark.asyncio
async def test_read_settings_empty(logged_client):
    client, *_ = await logged_client()
    response = client.get('/system-settings')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'settings': []}


@pytest.mark.asyncio
async def test_read_settings_basic_list(logged_client, create_system_setting):
    client, *_ = await logged_client()

    await create_system_setting(key='SETTING_1', value='1')
    await create_system_setting(key='SETTING_2', value='2')

    response = client.get('/system-settings')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data['settings']) == 2
    keys = [s['key'] for s in data['settings']]
    assert 'SETTING_1' in keys
    assert 'SETTING_2' in keys


@pytest.mark.asyncio
async def test_read_settings_pagination(logged_client, create_system_setting):
    client, *_ = await logged_client()

    for i in range(15):
        await create_system_setting(key=f'KEY_{i:02d}', value=str(i))

    response_page_1 = client.get(
        '/system-settings', params={'limit': 10, 'offset': 0}
    )
    data_1 = response_page_1.json()
    assert len(data_1['settings']) == 10

    response_page_2 = client.get(
        '/system-settings', params={'limit': 10, 'offset': 10}
    )
    data_2 = response_page_2.json()
    assert len(data_2['settings']) == 5


@pytest.mark.asyncio
async def test_read_settings_ignores_deleted(
    logged_client, create_system_setting
):
    client, *_ = await logged_client()

    active = await create_system_setting(key='ACTIVE_KEY', value='1')
    deleted = await create_system_setting(key='DELETED_KEY', value='2')

    # Deleta um
    client.delete(f'/system-settings/{deleted.key}')

    response = client.get('/system-settings')
    data = response.json()

    assert len(data['settings']) == 1
    assert data['settings'][0]['key'] == active.key


@pytest.mark.asyncio
async def test_update_setting_success(logged_client, create_system_setting):
    client, *_ = await logged_client()
    setting = await create_system_setting(key='UPDATABLE_KEY', value='old')

    payload = {'value': 'new_value'}
    response = client.put(f'/system-settings/{setting.key}', json=payload)

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['key'] == 'UPDATABLE_KEY'
    assert data['value'] == 'new_value'


@pytest.mark.asyncio
async def test_update_setting_not_found(logged_client):
    client, *_ = await logged_client()
    payload = {'value': 'new_value'}

    response = client.put('/system-settings/NON_EXISTENT_KEY', json=payload)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Setting not found'}


@pytest.mark.asyncio
async def test_delete_setting_success(logged_client, create_system_setting):
    client, *_ = await logged_client()
    setting = await create_system_setting(key='TO_DELETE', value='val')

    response = client.delete(f'/system-settings/{setting.key}')

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {'message': 'Setting successfully deactivated'}


@pytest.mark.asyncio
async def test_delete_setting_already_deleted(
    logged_client, create_system_setting
):
    client, *_ = await logged_client()
    setting = await create_system_setting(key='DOUBLE_DELETE', value='val')

    # Primeira deleção
    client.delete(f'/system-settings/{setting.key}')

    # Segunda deleção
    response = client.delete(f'/system-settings/{setting.key}')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Setting not found'}


@pytest.mark.asyncio
async def test_delete_setting_not_found(logged_client):
    client, *_ = await logged_client()
    response = client.delete('/system-settings/UNKNOWN_KEY')

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == {'detail': 'Setting not found'}


@pytest.mark.asyncio
async def test_read_setting_by_key(logged_client, create_system_setting):
    client, *_ = await logged_client()
    setting = await create_system_setting(key='MY_KEY', value='my_val')

    response = client.get(f'/system-settings/{setting.key}')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['key'] == 'MY_KEY'


@pytest.mark.asyncio
async def test_read_setting_by_id(logged_client, create_system_setting):
    client, *_ = await logged_client()
    setting = await create_system_setting(key='ID_TEST_KEY', value='id_val')

    response = client.get(f'/system-settings/{setting.key}')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == str(setting.id)
    assert response.json()['key'] == 'ID_TEST_KEY'


@pytest.mark.asyncio
async def test_read_setting_not_found(logged_client):
    client, *_ = await logged_client()

    # Testando com um ID inválido
    response_id = client.get('/system-settings/99999')
    assert response_id.status_code == HTTPStatus.NOT_FOUND

    # Testando com uma KEY inválida
    response_key = client.get('/system-settings/INVALID_KEY')
    assert response_key.status_code == HTTPStatus.NOT_FOUND
