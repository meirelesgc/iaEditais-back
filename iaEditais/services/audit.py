import logging
from typing import Any, Optional
from uuid import UUID

from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import AuditLog

# Configuração de Logs e Tracing
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


async def register_action(
    session: AsyncSession,
    user_id: UUID,
    action: str,
    table_name: str,
    record_id: UUID,
    old_data: Optional[dict[str, Any]] = None,
):
    audit_entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_data=old_data,
        user_id=user_id,
    )
    session.add(audit_entry)

    attributes = {
        'audit.table': table_name,
        'audit.action': action,
        'audit.record_id': str(record_id),
        'audit.user_id': str(user_id),
    }

    logger.info(
        f'Audit: User {user_id} performed {action} on {table_name}:{record_id}',
        extra=attributes,
    )

    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event('audit_log_created', attributes=attributes)
