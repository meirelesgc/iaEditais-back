from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .document_history import DocumentHistoryPublic
from .typification import TypificationPublic
from .user import UserFilter, UserPublic


class DocumentSchema(BaseModel):
    name: str
    identifier: str
    description: Optional[str] = None


class DocumentCreate(DocumentSchema):
    typification_ids: Optional[list[UUID]]
    editors_ids: Optional[list[UUID]]


class DocumentUpdate(DocumentSchema):
    id: UUID
    typification_ids: Optional[list[UUID]]
    editors_ids: Optional[list[UUID]]


class DocumentPublic(DocumentSchema):
    id: UUID
    history: list[DocumentHistoryPublic]
    typifications: list[TypificationPublic]
    editors: list[UserPublic]
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    documents: list[DocumentPublic]


class DocumentFilter(UserFilter):
    unit_id: Optional[UUID] = None
