from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from iaEditais.schemas.user import UserFilter, UserPublic


class AuditLogPublic(BaseModel):
    id: UUID
    table_name: str
    record_id: UUID
    action: str
    user_id: UUID
    old_data: Optional[dict] = None
    user: UserPublic
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AuditLogList(BaseModel):
    audit_logs: list[AuditLogPublic]


class AuditLogFilter(UserFilter):
    table_name: Optional[str] = None
    record_id: Optional[UUID] = None
    action: Optional[str] = None
    user_id: Optional[UUID] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None
    search: Optional[str] = None
    order: Optional[str] = 'desc'
