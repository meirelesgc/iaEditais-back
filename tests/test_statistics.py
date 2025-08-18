from http import HTTPStatus

import pytest


@pytest.mark.asyncio
async def test_get_general_summary(
    client,
    create_unit,
    create_user,
    create_doc,
    create_release,
    create_typification,
):
    EXPECTED_UNITS = 2
    EXPECTED_USERS = 3
    EXPECTED_DOCS = 1
    EXPECTED_RELEASES = 2
    EXPECTED_TYPIFICATIONS = 4
    for _ in range(EXPECTED_UNITS):
        unit = await create_unit()

    for _ in range(EXPECTED_USERS):
        await create_user(unit_id=unit.id)

    for _ in range(EXPECTED_TYPIFICATIONS):
        typification = await create_typification()

    for _ in range(EXPECTED_DOCS):
        doc = await create_doc(typification=[typification.id])

    for _ in range(EXPECTED_RELEASES):
        await create_release(doc)

    response = client.get('/statistics/general-summary')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data['total_units'] == EXPECTED_UNITS
    assert data['total_users'] == EXPECTED_USERS
    assert data['total_docs'] == EXPECTED_DOCS
    assert data['total_releases'] == EXPECTED_RELEASES
    assert data['total_typifications'] == EXPECTED_TYPIFICATIONS


@pytest.mark.asyncio
async def test_get_typification_usage(client, create_doc, create_typification):
    DOCS_TYP1 = 2
    DOCS_TYP2 = 1

    typ1 = await create_typification(name='Contratação Direta')
    typ2 = await create_typification(name='Pregão Eletrônico')

    [await create_doc(typification=[typ1.id]) for _ in range(DOCS_TYP1)]
    [await create_doc(typification=[typ2.id]) for _ in range(DOCS_TYP2)]

    response = client.get('/statistics/typification-usage')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 2
    assert data[0]['name'] == 'Contratação Direta'
    assert data[0]['doc_count'] == DOCS_TYP1
    assert data[1]['name'] == 'Pregão Eletrônico'
    assert data[1]['doc_count'] == DOCS_TYP2


@pytest.mark.asyncio
async def test_get_users_per_unit(client, create_unit, create_user):
    USERS_IN_UNIT_A = 2
    USERS_IN_UNIT_B = 1

    unit_a = await create_unit(name='Licitações')
    unit_b = await create_unit(name='Contratos')
    unit_c = await create_unit(name='TI')

    for _ in range(USERS_IN_UNIT_A):
        await create_user(unit_id=unit_a.id)

    for _ in range(USERS_IN_UNIT_B):
        await create_user(unit_id=unit_b.id)

    response = client.get('/statistics/users-per-unit')

    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == 3

    unit_data = {item['name']: item['user_count'] for item in data}
    assert unit_data['Licitações'] == USERS_IN_UNIT_A
    assert unit_data['Contratos'] == USERS_IN_UNIT_B
    assert unit_data['TI'] == 0


@pytest.mark.asyncio
async def test_get_activity_by_access_level(client, create_user):
    EXPECTED_ADMINS = 1
    EXPECTED_ANALYSTS = 2
    EXPECTED_DEFAULTS = 3

    for _ in range(EXPECTED_ADMINS):
        await create_user(access_level='ADMIN')

    for _ in range(EXPECTED_ANALYSTS):
        await create_user(access_level='ANALYST')

    for _ in range(EXPECTED_DEFAULTS):
        await create_user(access_level='DEFAULT')

    response = client.get('/statistics/activity-by-access-level')

    assert response.status_code == HTTPStatus.OK
    data = response.json()

    access_level_counts = {
        item['access_level']: item['user_count'] for item in data
    }

    assert access_level_counts.get('ADMIN', 0) == EXPECTED_ADMINS
    assert access_level_counts.get('ANALYST', 0) == EXPECTED_ANALYSTS
    assert access_level_counts.get('DEFAULT', 0) == EXPECTED_DEFAULTS
