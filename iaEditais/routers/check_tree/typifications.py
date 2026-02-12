from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.schemas import (
    TypificationCreate,
    TypificationFilter,
    TypificationList,
    TypificationPublic,
    TypificationUpdate,
)
from iaEditais.services import typification_service

router = APIRouter(
    prefix='/typification',
    tags=['árvore de verificação, tipificações'],
)


@router.post(
    '',
    status_code=HTTPStatus.CREATED,
    response_model=TypificationPublic,
)
async def create_typification(
    typification: TypificationCreate,
    session: Session,
    current_user: CurrentUser,
):
    return await typification_service.create_typification(
        session, current_user.id, typification
    )


@router.get('', response_model=TypificationList)
async def read_typifications(
    session: Session, filters: Annotated[TypificationFilter, Depends()]
):
    typifications = await typification_service.get_typifications(
        session, filters
    )
    return {'typifications': typifications}


@router.get('/{typification_id}', response_model=TypificationPublic)
async def read_typification(typification_id: UUID, session: Session):
    return await typification_service.get_typification_by_id(
        session, typification_id
    )


@router.put('', response_model=TypificationPublic)
async def update_typification(
    typification: TypificationUpdate,
    session: Session,
    current_user: CurrentUser,
):
    return await typification_service.update_typification(
        session, current_user.id, typification
    )


@router.delete(
    '/{typification_id}',
    status_code=HTTPStatus.NO_CONTENT,
)
async def delete_typification(
    typification_id: UUID,
    session: Session,
    current_user: CurrentUser,
):
    await typification_service.delete_typification(
        session, current_user.id, typification_id
    )
    return {'message': 'Typification deleted'}


@router.get('/export/pdf')
async def exportar_tipificacoes_pdf(
    session: Session,
    typification_id: UUID = None,
):
    return await typification_service.export_pdf(session, typification_id)
