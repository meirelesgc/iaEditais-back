from http import HTTPStatus

import pytest

from tests.factories import user_factory

# Você pode ajustar este valor base se tiver usuários criados por padrão no DB de teste
BASE_USERS = 0

# ======================================================
# Testes para POST /user/
# ======================================================


@pytest.mark.asyncio
async def test_post_user_as_admin_success(login, create_admin_user, create_unit):
    """
    Cenário: Admin cria um novo usuário com sucesso.
    Resultado esperado: Status 201 CREATED.
    """
    admin_user = await create_admin_user()
    client = login(admin_user)

    unit = await create_unit()
    user_to_create = user_factory.CreateUserFactory(unit_id=unit.id)

    response = client.post('/user/', json=user_to_create.model_dump(mode='json'))

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()['email'] == user_to_create.email


@pytest.mark.asyncio
async def test_post_user_as_default_user_forbidden(
    login, create_user, create_unit
):
    """
    Cenário: Usuário comum tenta criar um novo usuário.
    Resultado esperado: Status 403 FORBIDDEN.
    """
    default_user = await create_user()
    client = login(default_user)

    unit = await create_unit()
    user_to_create = user_factory.CreateUserFactory(unit_id=unit.id)

    response = client.post('/user/', json=user_to_create.model_dump(mode='json'))

    assert response.status_code == HTTPStatus.FORBIDDEN


# ======================================================
# Testes para GET /user/ (Listar todos)
# ======================================================


@pytest.mark.asyncio
async def test_get_all_users_as_admin_success(
    login, create_admin_user, create_user
):
    """
    Cenário: Admin lista todos os usuários.
    Resultado esperado: Status 200 OK e a lista de usuários.
    """
    admin_user = await create_admin_user()
    client = login(admin_user)

    # Cria alguns usuários para popular a lista
    await create_user()
    await create_user()

    response = client.get('/user/')

    # O +1 é para contar o próprio admin que está logado
    assert response.status_code == HTTPStatus.OK
    assert len(response.json()) == 2 + 1 + BASE_USERS


@pytest.mark.asyncio
async def test_get_all_users_as_default_user_forbidden(login, create_user):
    """
    Cenário: Usuário comum tenta listar todos os usuários.
    Resultado esperado: Status 403 FORBIDDEN.
    """
    default_user = await create_user()
    client = login(default_user)

    response = client.get('/user/')

    assert response.status_code == HTTPStatus.FORBIDDEN


# ======================================================
# Testes para GET /user/my-self/
# ======================================================


@pytest.mark.asyncio
async def test_get_self_success(login, create_user):
    """
    Cenário: Um usuário logado busca suas próprias informações.
    Resultado esperado: Status 200 OK e os dados corretos.
    """
    user = await create_user()
    client = login(user)

    response = client.get('/user/my-self/')

    assert response.status_code == HTTPStatus.OK
    assert response.json().get('id') == str(user.id)


# ======================================================
# Testes para GET /user/{id}/ (Buscar um específico)
# ======================================================


@pytest.mark.asyncio
async def test_get_single_user_as_admin_success(
    login, create_admin_user, create_user
):
    """
    Cenário: Admin busca um usuário específico pelo ID.
    Resultado esperado: Status 200 OK.
    """
    admin_user = await create_admin_user()
    client = login(admin_user)

    user_to_find = await create_user()

    response = client.get(f'/user/{user_to_find.id}/')

    assert response.status_code == HTTPStatus.OK
    assert response.json()['id'] == str(user_to_find.id)


@pytest.mark.asyncio
async def test_get_single_user_as_default_user_forbidden(login, create_user):
    """
    Cenário: Usuário comum tenta buscar outro usuário pelo ID.
    Resultado esperado: Status 403 FORBIDDEN.
    """
    default_user = await create_user()
    client = login(default_user)

    other_user = await create_user()

    response = client.get(f'/user/{other_user.id}/')

    assert response.status_code == HTTPStatus.FORBIDDEN


# ======================================================
# Testes para PUT /user/
# ======================================================


@pytest.mark.asyncio
async def test_put_update_self_success(login, create_user):
    """
    Cenário: Usuário comum atualiza seus próprios dados.
    Resultado esperado: Status 200 OK.
    """
    user = await create_user()
    client = login(user)

    update_data = user.model_dump(mode='json')
    update_data['username'] = 'Nome Atualizado'

    response = client.put('/user/', json=update_data)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['username'] == 'Nome Atualizado'


@pytest.mark.asyncio
async def test_put_update_other_user_as_default_user_forbidden(
    login, create_user
):
    """
    Cenário: Usuário comum tenta atualizar os dados de outro usuário.
    Resultado esperado: Status 403 FORBIDDEN.
    """
    default_user = await create_user()
    client = login(default_user)

    other_user = await create_user()
    update_data = other_user.model_dump(mode='json')
    update_data['username'] = 'Tentativa de Update'

    response = client.put('/user/', json=update_data)

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_put_update_other_user_as_admin_success(
    login, create_admin_user, create_user
):
    """
    Cenário: Admin atualiza os dados de outro usuário.
    Resultado esperado: Status 200 OK.
    """
    admin_user = await create_admin_user()
    client = login(admin_user)

    user_to_update = await create_user()
    update_data = user_to_update.model_dump(mode='json')
    update_data['username'] = 'Atualizado pelo Admin'

    response = client.put('/user/', json=update_data)

    assert response.status_code == HTTPStatus.OK
    assert response.json()['username'] == 'Atualizado pelo Admin'


@pytest.mark.asyncio
async def test_put_promote_user_to_admin_as_default_user_forbidden(
    login, create_user
):
    """
    Cenário: Usuário comum tenta se promover para admin.
    Resultado esperado: Status 403 FORBIDDEN.
    """
    user = await create_user()
    client = login(user)

    update_data = user.model_dump(mode='json')
    update_data['access_level'] = 'ADMIN'

    response = client.put('/user/', json=update_data)

    assert response.status_code == HTTPStatus.FORBIDDEN


# ======================================================
# Testes para DELETE /user/{id}/
# ======================================================


@pytest.mark.asyncio
async def test_delete_self_success(login, create_user):
    """
    Cenário: Usuário comum deleta a própria conta.
    Resultado esperado: Status 204 NO CONTENT.
    """
    user = await create_user()
    client = login(user)

    response = client.delete(f'/user/{user.id}/')

    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.mark.asyncio
async def test_delete_other_user_as_default_user_forbidden(login, create_user):
    """
    Cenário: Usuário comum tenta deletar a conta de outro usuário.
    Resultado esperado: Status 403 FORBIDDEN.
    """
    default_user = await create_user()
    client = login(default_user)

    other_user = await create_user()

    response = client.delete(f'/user/{other_user.id}/')

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio
async def test_delete_other_user_as_admin_success(
    login, create_admin_user, create_user
):
    """
    Cenário: Admin deleta a conta de outro usuário.
    Resultado esperado: Status 204 NO CONTENT.
    """
    admin_user = await create_admin_user()
    client = login(admin_user)

    user_to_delete = await create_user()

    response = client.delete(f'/user/{user_to_delete.id}/')

    assert response.status_code == HTTPStatus.NO_CONTENT
