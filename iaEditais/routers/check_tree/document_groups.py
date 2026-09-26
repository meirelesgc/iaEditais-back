from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from iaEditais.core.dependencies import CurrentUser, Session, Storage
from iaEditais.schemas.document_group import (
    DocumentGroupCreate,
    DocumentGroupFilter,
    DocumentGroupItemCreate,
    DocumentGroupItemPublic,
    DocumentGroupItemUpdate,
    DocumentGroupList,
    DocumentGroupPublic,
    DocumentGroupUpdate,
)
from iaEditais.services import document_group_service

router = APIRouter(
    prefix='/document-group',
    tags=['configurador, grupos de documentos'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentGroupPublic,
    summary='Criar grupo de documento',
    description='Cria um novo grupo de documento no configurador.',
)
async def create_group(
    group: DocumentGroupCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.create_group(
        session, current_user.id, group
    )


@router.get(
    '',
    response_model=DocumentGroupList,
    summary='Listar grupos de documento',
    description='Retorna todos os grupos de documento cadastrados, com filtro opcional por nome.',
)
async def read_groups(
    session: Session,
    filters: Annotated[DocumentGroupFilter, Depends()],
):
    groups = await document_group_service.get_groups(session, filters)
    return {'groups': groups}


@router.get(
    '/{group_id}',
    response_model=DocumentGroupPublic,
    summary='Obter grupo de documento por ID',
    description='Retorna um grupo de documento específico pelo seu UUID.',
)
async def read_group(group_id: UUID, session: Session):
    return await document_group_service.get_group_by_id(session, group_id)


@router.put(
    '',
    response_model=DocumentGroupPublic,
    summary='Atualizar grupo de documento',
    description='Atualiza os dados de um grupo de documento existente.',
)
async def update_group(
    group: DocumentGroupUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.update_group(
        session, current_user.id, group
    )


@router.delete(
    '/{group_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir grupo de documento',
    description='Remove (soft-delete) um grupo de documento. Itens associados serão removidos em cascata.',
)
async def delete_group(
    group_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await document_group_service.delete_group(
        session, current_user.id, group_id
    )
    return {'message': 'Document group deleted'}


@router.post(
    '/{group_id}/item',
    status_code=HTTPStatus.CREATED,
    response_model=DocumentGroupItemPublic,
    summary='Criar item de grupo',
    description='Adiciona um novo item a um grupo de documento existente.',
)
async def create_item(
    group_id: UUID,
    item: DocumentGroupItemCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.create_item(
        session, current_user.id, group_id, item
    )


@router.get(
    '/{group_id}/items',
    response_model=list[DocumentGroupItemPublic],
    summary='Listar itens de um grupo',
    description='Retorna todos os itens pertencentes a um grupo de documento específico.',
)
async def read_items_by_group(group_id: UUID, session: Session):
    from iaEditais.repositories import document_group_repo

    return await document_group_repo.get_items_by_group(session, group_id)


@router.put(
    '/item',
    response_model=DocumentGroupItemPublic,
    summary='Atualizar item de grupo',
    description='Atualiza o nome de um item de grupo de documento.',
)
async def update_item(
    item: DocumentGroupItemUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await document_group_service.update_item(
        session, current_user.id, item
    )


@router.delete(
    '/item/{item_id}',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Excluir item de grupo',
    description='Remove (soft-delete) um item de grupo de documento.',
)
async def delete_item(
    item_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await document_group_service.delete_item(
        session, current_user.id, item_id
    )
    return {'message': 'Document group item deleted'}


@router.post(
    '/item/{item_id}/icon',
    response_model=DocumentGroupItemPublic,
    summary='Enviar imagem do item',
    description=(
        'Salva a imagem do item como arquivo e grava em icon_path a URL gerada. '
        'Substitui a imagem anterior, se houver.'
    ),
)
async def set_item_icon(
    item_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
    file: UploadFile = File(...),
):
    return await document_group_service.update_item_icon(
        session, current_user.id, item_id, file, storage
    )


@router.delete(
    '/item/{item_id}/icon',
    status_code=HTTPStatus.NO_CONTENT,
    summary='Remover imagem do item',
    description='Exclui o arquivo da imagem do item e limpa o icon_path.',
)
async def delete_item_icon(
    item_id: UUID,
    session: Session,
    current_user: CurrentUser,
    storage: Storage,
):
    await document_group_service.delete_item_icon(
        session, current_user.id, item_id, storage
    )
    return {'message': 'Document group item icon deleted'}
