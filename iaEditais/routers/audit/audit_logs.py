from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select

from iaEditais.core.dependencies import Session
from iaEditais.models import AuditLog, User
from iaEditais.schemas import AuditLogFilter, AuditLogList

router = APIRouter(prefix='/audit-log', tags=['auditoria'])


@router.get('/', response_model=AuditLogList)
async def read_audit_logs(
    session: Session, filters: Annotated[AuditLogFilter, Depends()]
):
    query = select(AuditLog).join(User, User.id == AuditLog.user_id)

    if filters.table_name:
        query = query.where(
            AuditLog.table_name.ilike(f'%{filters.table_name}%')
        )

    if filters.record_id:
        query = query.where(AuditLog.record_id == filters.record_id)

    if filters.action:
        query = query.where(AuditLog.action.ilike(f'%{filters.action}%'))

    if filters.user_id:
        query = query.where(AuditLog.user_id == filters.user_id)

    if filters.created_from:
        query = query.where(AuditLog.created_at >= filters.created_from)

    if filters.created_to:
        query = query.where(AuditLog.created_at <= filters.created_to)

    if filters.search:
        s = f'%{filters.search}%'
        query = query.where(
            or_(
                AuditLog.table_name.ilike(s),
                AuditLog.action.ilike(s),
                func.cast(AuditLog.record_id, func.text).ilike(s),
                func.cast(AuditLog.user_id, func.text).ilike(s),
                func.cast(AuditLog.old_data, func.text).ilike(s),
            )
        )

    if (filters.order or '').lower() == 'asc':
        query = query.order_by(AuditLog.created_at.asc())
    else:
        query = query.order_by(AuditLog.created_at.desc())

    query = query.offset(filters.offset).limit(filters.limit)

    result = await session.scalars(query)
    logs = result.all()

    return {'audit_logs': logs}
