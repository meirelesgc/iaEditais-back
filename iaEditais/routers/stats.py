from typing import List

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import desc, func, join, select

from iaEditais.core.dependencies import Session
from iaEditais.models import (
    AppliedTypification,
    Document,
    DocumentHistory,
    DocumentMessage,
    DocumentRelease,
    Unit,
    User,
)

# --- Schemas de Resposta para Estatísticas ---


class DocumentCountByUnit(BaseModel):
    """Estatística de contagem de documentos por unidade."""

    unit_name: str
    document_count: int


class DocumentCountByUnitList(BaseModel):
    stats: List[DocumentCountByUnit]


class TypificationUsage(BaseModel):
    """Estatística de uso de tipificações."""

    typification_name: str
    usage_count: int


class TypificationUsageList(BaseModel):
    stats: List[TypificationUsage]


class KpiStats(BaseModel):
    """KPIs gerais do sistema."""

    total_users: int
    total_documents: int
    total_units: int
    total_analyses: int  # Contagem de DocumentRelease


class UserMessageActivity(BaseModel):
    """Estatística de atividade de usuários por mensagens."""

    username: str
    message_count: int


class UserMessageActivityList(BaseModel):
    stats: List[UserMessageActivity]


# --- Router de Estatísticas ---

router = APIRouter(
    prefix='/stats', tags=['operações de sistema, estatísticas']
)


@router.get(
    '/documents-by-unit',
    response_model=DocumentCountByUnitList,
    summary='Contagem de documentos analisados por unidade',
)
async def get_document_count_by_unit(session: Session):
    """
    Retorna a contagem de documentos ativos (não deletados)
    agrupados por unidade.
    """
    statement = (
        select(
            Unit.name.label('unit_name'),
            func.count(Document.id).label('document_count'),
        )
        .select_from(join(Unit, Document, Unit.id == Document.unit_id))
        .where(Unit.deleted_at.is_(None), Document.deleted_at.is_(None))
        .group_by(Unit.id, Unit.name)
        .order_by(desc('document_count'))
    )

    result = await session.execute(statement)
    stats = result.mappings().all()  # .mappings() converte para dict-like

    return {'stats': stats}


@router.get(
    '/most-used-typifications',
    response_model=TypificationUsageList,
    summary='Top 10 tipificações mais utilizadas nas análises',
)
async def get_most_used_typifications(session: Session):
    """
    Retorna as 10 tipificações mais aplicadas (com base em
    'AppliedTypification') em documentos ativos.
    """
    statement = (
        select(
            AppliedTypification.name.label('typification_name'),
            func.count(AppliedTypification.id).label('usage_count'),
        )
        .join(
            DocumentRelease,
            AppliedTypification.applied_release_id == DocumentRelease.id,
        )
        .join(
            DocumentHistory,
            DocumentRelease.history_id == DocumentHistory.id,
        )
        .join(Document, DocumentHistory.document_id == Document.id)
        .where(Document.deleted_at.is_(None))  # Apenas de documentos ativos
        .group_by(AppliedTypification.name)
        .order_by(desc('usage_count'))
        .limit(10)
    )

    result = await session.execute(statement)
    stats = result.mappings().all()

    return {'stats': stats}


@router.get(
    '/kpis',
    response_model=KpiStats,
    summary='Indicadores chave de performance (KPIs) gerais',
)
async def get_kpis(session: Session):
    """
    Retorna métricas gerais do sistema, como total de usuários,
    documentos, unidades e análises (releases) em documentos ativos.
    """

    # Total de Usuários Ativos
    stmt_users = select(func.count(User.id)).where(User.deleted_at.is_(None))
    total_users = await session.scalar(stmt_users) or 0

    # Total de Documentos Ativos
    stmt_docs = select(func.count(Document.id)).where(
        Document.deleted_at.is_(None)
    )
    total_documents = await session.scalar(stmt_docs) or 0

    # Total de Unidades Ativas
    stmt_units = select(func.count(Unit.id)).where(Unit.deleted_at.is_(None))
    total_units = await session.scalar(stmt_units) or 0

    # Total de Análises (Releases) de Documentos Ativos
    stmt_analyses = (
        select(func.count(DocumentRelease.id))
        .join(
            DocumentHistory,
            DocumentRelease.history_id == DocumentHistory.id,
        )
        .join(Document, DocumentHistory.document_id == Document.id)
        .where(Document.deleted_at.is_(None))
    )
    total_analyses = await session.scalar(stmt_analyses) or 0

    return KpiStats(
        total_users=total_users,
        total_documents=total_documents,
        total_units=total_units,
        total_analyses=total_analyses,
    )


@router.get(
    '/user-message-activity',
    response_model=UserMessageActivityList,
    summary='Top 5 usuários mais ativos por mensagens',
)
async def get_user_message_activity(session: Session):
    """
    Retorna os 5 usuários mais ativos com base no número de mensagens
    enviadas (excluindo usuários e mensagens deletadas).
    """
    statement = (
        select(
            User.username,
            func.count(DocumentMessage.id).label('message_count'),
        )
        .join(DocumentMessage, User.id == DocumentMessage.author_id)
        .where(
            User.deleted_at.is_(None),
            DocumentMessage.deleted_at.is_(None),
        )
        .group_by(User.id, User.username)
        .order_by(desc('message_count'))
        .limit(5)
    )

    result = await session.execute(statement)
    stats = result.mappings().all()

    return {'stats': stats}
