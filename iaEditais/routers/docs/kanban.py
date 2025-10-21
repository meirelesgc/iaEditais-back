import re
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException

from iaEditais.core.dependencies import CurrentUser, Session
from iaEditais.models import Document, DocumentHistory, DocumentStatus, User
from iaEditais.schemas import DocumentPublic

URL = 'http://localhost:8080/message/sendText/Gleidson'
HEADERS = {'Content-Type': 'application/json', 'apikey': 'secret'}

router = APIRouter(
    prefix='/doc/{doc_id}/status', tags=['verificação dos documentos, kanban']
)


class NotifyTarget(str, Enum):
    EDITORS = 'editors'
    CREATOR = 'creator'


NOTIFICATION_RULES: dict[
    DocumentStatus, dict[str, bool | NotifyTarget | list[NotifyTarget]]
] = {
    DocumentStatus.UNDER_CONSTRUCTION: {
        'enabled': True,
        'targets': [NotifyTarget.EDITORS],
    },
    DocumentStatus.WAITING_FOR_REVIEW: {
        'enabled': True,
        'targets': [NotifyTarget.CREATOR],
    },
    DocumentStatus.PENDING: {
        'enabled': False,
        'targets': [],
    },
    DocumentStatus.COMPLETED: {
        'enabled': False,
        'targets': [],
    },
}


async def get_doc_or_404(doc_id: UUID, session: Session) -> Document:
    doc = await session.get(Document, doc_id)
    if not doc or doc.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Doc not found',
        )
    return doc


async def _set_status(
    doc: Document, status: DocumentStatus, user: User, session: Session
) -> Document:
    history = DocumentHistory(
        document_id=doc.id,
        status=status.value,
        created_by=user.id,
    )
    session.add(history)
    doc.updated_by = user.id
    doc.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(doc)
    return doc


async def _notify_users(
    doc: Document, status: DocumentStatus, session: Session
):
    status_para_portugues = {
        DocumentStatus.PENDING: 'Pendente',
        DocumentStatus.UNDER_CONSTRUCTION: 'Em construção',
        DocumentStatus.WAITING_FOR_REVIEW: 'Aguardando revisão',
        DocumentStatus.COMPLETED: 'Concluído',
    }

    rules = NOTIFICATION_RULES.get(status, {'enabled': False})
    if not rules['enabled']:
        return

    targets = []
    for target in rules['targets']:
        if target == NotifyTarget.EDITORS:
            targets.extend(doc.editors)
        elif target == NotifyTarget.CREATOR and doc.created_by:
            creator = await session.get(User, doc.created_by)
            if creator:
                targets.append(creator)

    async with httpx.AsyncClient() as client:
        for user in targets:
            if not user.phone_number:
                continue

            numero = (
                user.phone_number.strip().replace(' ', '').replace('-', '')
            )
            if not re.fullmatch(r'55\d{10,11}', numero):
                print(
                    f'[ERRO] Número de telefone inválido para {user.username}: {numero}'
                )
                continue

            status_traduzido = status_para_portugues.get(status, status.value)

            payload = {
                'number': numero,
                'text': (
                    f"Olá {user.username}, o documento '{doc.name}' "
                    f'foi atualizado para o status: {status_traduzido}'
                ),
            }

            response = await client.post(URL, headers=HEADERS, json=payload)
            if response.status_code != HTTPStatus.CREATED:
                print(
                    f'[ERRO] Falha ao enviar mensagem para {user.username}: {response.text}'
                )


@router.put('/pending', response_model=DocumentPublic)
async def set_status_pending(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    await _notify_users(doc, DocumentStatus.PENDING, session)
    await _set_status(doc, DocumentStatus.PENDING, current_user, session)
    return doc


@router.put('/under-construction', response_model=DocumentPublic)
async def set_status_under_construction(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    await _notify_users(doc, DocumentStatus.UNDER_CONSTRUCTION, session)
    return await _set_status(
        doc, DocumentStatus.UNDER_CONSTRUCTION, current_user, session
    )


@router.put('/waiting-review', response_model=DocumentPublic)
async def set_status_waiting_review(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    await _notify_users(doc, DocumentStatus.WAITING_FOR_REVIEW, session)
    return await _set_status(
        doc, DocumentStatus.WAITING_FOR_REVIEW, current_user, session
    )


@router.put('/completed', response_model=DocumentPublic)
async def set_status_completed(
    doc_id: UUID, session: Session, current_user: CurrentUser
):
    doc = await get_doc_or_404(doc_id, session)
    await _notify_users(doc, DocumentStatus.COMPLETED, session)
    return await _set_status(
        doc, DocumentStatus.COMPLETED, current_user, session
    )
