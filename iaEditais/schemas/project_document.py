from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectDocumentSchema(BaseModel):
    type: Optional[str] = None
    name: str
    number: Optional[str] = None
    status: Optional[str] = 'PENDING'
    responsible: Optional[UUID] = None
    responsibles: Optional[list[UUID]] = None
    typification_ids: Optional[list[str]] = None


class ProjectDocumentCreate(ProjectDocumentSchema):
    project_id: UUID


class ProjectDocumentUpdate(BaseModel):
    id: UUID
    type: Optional[str] = None
    name: Optional[str] = None
    number: Optional[str] = None
    status: Optional[str] = None
    responsible: Optional[UUID] = None
    responsibles: Optional[list[UUID]] = None
    sent_to_kanban: Optional[bool] = None
    typification_ids: Optional[list[str]] = None


class ProjectDocumentPublic(ProjectDocumentSchema):
    id: UUID
    project_id: UUID
    sent_to_kanban: bool
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectDocumentList(BaseModel):
    documents: list[ProjectDocumentPublic]
