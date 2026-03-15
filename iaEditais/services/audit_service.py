import logging
from typing import Any, Optional
from uuid import UUID

from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import AuditLog
from iaEditais.schemas import DocumentStatus

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

STATUS_TRANSLATION = {
    DocumentStatus.PENDING: 'Pendente',
    DocumentStatus.UNDER_CONSTRUCTION: 'Em construção',
    DocumentStatus.WAITING_FOR_REVIEW: 'Aguardando revisão',
    DocumentStatus.COMPLETED: 'Concluído',
}


def _format_value(value: Any) -> str:
    if value is None:
        return 'Vazio'
    if value is True:
        return 'Sim'
    if value is False:
        return 'Não'

    if isinstance(value, DocumentStatus):
        return STATUS_TRANSLATION.get(value, str(value.value))

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
        'status': 'Status',
    }

    for key, new_val in new_data.items():
        if key in ignore_keys:
            continue

        old_val = old_data.get(key)

        if (
            key == 'history'
            and isinstance(old_val, list)
            and isinstance(new_val, list)
        ):
            old_item = old_val[0] if old_val else {}
            new_item = new_val[0] if new_val else {}

            old_status_raw = old_item.get('status')
            new_status_raw = new_item.get('status')

            if old_status_raw != new_status_raw:
                old_status = STATUS_TRANSLATION.get(
                    old_status_raw, old_status_raw or 'Sem status'
                )
                new_status = STATUS_TRANSLATION.get(
                    new_status_raw, new_status_raw or 'Sem status'
                )
                changes.append(
                    f"Moveu o documento da etapa '{old_status}' para '{new_status}'"
                )
            continue

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
