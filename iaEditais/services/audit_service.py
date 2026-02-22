import logging
from typing import Any, Optional
from uuid import UUID

from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import AuditLog

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def _format_value(value: Any) -> str:
    if value is None:
        return 'Vazio'
    if value is True:
        return 'Sim'
    if value is False:
        return 'Não'

    if isinstance(value, (dict, list)):
        return 'Configurado'

    return str(value)


def _generate_human_diff(
    action: str, old_data: Optional[dict], new_data: Optional[dict]
) -> str:
    if action == 'CREATE':
        return 'Registro criado.'

    if action == 'DELETE':
        return 'Registro removido.'

    if not old_data or not new_data:
        return 'Registro alterado.'

    changes = []
    ignore_keys = {'_sa_instance_state', 'updated_at'}

    field_translation = {
        'is_active': 'Ativo',
        'created_at': 'Data de Criação',
        'name': 'Nome',
        'description': 'Descrição',
    }

    for key, new_val in new_data.items():
        if key in ignore_keys:
            continue

        old_val = old_data.get(key)

        if old_val != new_val:
            field_name = field_translation.get(
                key, key.replace('_', ' ').capitalize()
            )
            old_str = _format_value(old_val)
            new_str = _format_value(new_val)

            if old_str == new_str and old_str == 'Configurado':
                changes.append(f'{field_name} modificado')
            else:
                changes.append(
                    f"Alterou {field_name} de '{old_str}' para '{new_str}'"
                )

    if not changes:
        return 'Salvo sem alterações.'

    return '; '.join(changes)


async def register_action(
    session: AsyncSession,
    user_id: UUID,
    action: str,
    table_name: str,
    record_id: UUID,
    old_data: Optional[dict[str, Any]] = None,
    new_data: Optional[dict[str, Any]] = None,
):
    description = _generate_human_diff(action, old_data, new_data)

    audit_entry = AuditLog(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_data=old_data,
        user_id=user_id,
        description=description,
    )
    session.add(audit_entry)

    attributes = {
        'audit.table': table_name,
        'audit.action': action,
        'audit.record_id': str(record_id),
        'audit.user_id': str(user_id),
        'audit.diff': description,
    }

    logger.info(
        f'Audit: User {user_id} performed {action} on {table_name}:{record_id}. Diff: {description}',
        extra=attributes,
    )

    current_span = trace.get_current_span()
    if current_span.is_recording():
        current_span.add_event('audit_log_created', attributes=attributes)
