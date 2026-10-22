"""Testes das referencias de grupo e tipo nas sessoes de sugestao."""

from http import HTTPStatus
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from iaEditais.features.tree_suggestion import service
from iaEditais.models import DocumentGroup, DocumentGroupItem


class _FakeSession:
    """Session minima que resolve apenas `get` por modelo e id."""

    def __init__(self, entities: dict):
        self.entities = entities

    async def get(self, model, entity_id):
        return self.entities.get((model.__name__, entity_id))


def _group(group_id, name='Editais'):
    return SimpleNamespace(
        id=group_id,
        name=name,
        deleted_at=None,
    )


def _group_item(item_id, group_id, name='Pregao eletronico'):
    return SimpleNamespace(
        id=item_id,
        group_id=group_id,
        name=name,
        deleted_at=None,
    )


@pytest.mark.asyncio
async def test_validate_document_group_accepts_valid_pair():
    group_id, item_id = uuid4(), uuid4()
    session = _FakeSession(
        {
            ('DocumentGroup', group_id): _group(group_id),
            ('DocumentGroupItem', item_id): _group_item(item_id, group_id),
        }
    )

    resultado = await service._validate_document_group(
        session, group_id, item_id
    )

    assert resultado == (group_id, item_id)


@pytest.mark.asyncio
async def test_validate_document_group_allows_empty_reference():
    session = _FakeSession({})

    resultado = await service._validate_document_group(session, None, None)

    assert resultado == (None, None)


@pytest.mark.asyncio
async def test_validate_document_group_requires_item():
    group_id = uuid4()
    session = _FakeSession({('DocumentGroup', group_id): _group(group_id)})

    with pytest.raises(HTTPException) as excecao:
        await service._validate_document_group(session, group_id, None)

    assert excecao.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validate_document_group_rejects_item_outside_group():
    group_id, item_id = uuid4(), uuid4()
    session = _FakeSession(
        {
            ('DocumentGroup', group_id): _group(group_id),
            ('DocumentGroupItem', item_id): _group_item(item_id, uuid4()),
        }
    )

    with pytest.raises(HTTPException) as excecao:
        await service._validate_document_group(session, group_id, item_id)

    assert excecao.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_validate_document_group_rejects_unknown_group():
    group_id, item_id = uuid4(), uuid4()
    session = _FakeSession(
        {('DocumentGroupItem', item_id): _group_item(item_id, group_id)}
    )

    with pytest.raises(HTTPException) as excecao:
        await service._validate_document_group(session, group_id, item_id)

    assert excecao.value.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_apply_item_creates_typification_with_session_group(
    monkeypatch,
):
    group_id, item_id = uuid4(), uuid4()
    captured = {}

    async def fake_create_typification(
        session, user_id, data, commit=True
    ):
        captured['data'] = data
        return SimpleNamespace(id=uuid4())

    async def fake_list_confirmed(session, suggestion_id, kinds):
        return []

    monkeypatch.setattr(
        service.typification_service,
        'create_typification',
        fake_create_typification,
    )
    monkeypatch.setattr(
        service.tree_suggestion_repo,
        'list_confirmed',
        fake_list_confirmed,
    )

    suggestion = SimpleNamespace(
        id=uuid4(),
        document_group_id=group_id,
        document_group_item_id=item_id,
    )
    item = SimpleNamespace(kind='typification', operation='create')

    await service._apply_item(
        _FakeSession({}),
        uuid4(),
        suggestion,
        item,
        'Edital de Pregao',
        'Descricao',
    )

    assert captured['data'].document_group_id == group_id
    assert captured['data'].document_group_item_id == item_id
    assert captured['data'].name == 'Edital de Pregao'


def test_document_group_models_are_exported():
    assert DocumentGroup.__tablename__ == 'document_groups'
    assert DocumentGroupItem.__tablename__ == 'document_group_items'
