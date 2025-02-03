from pydantic import Field, BaseModel
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


class CreateDocument(BaseModel):
    name: str


class Document(CreateDocument):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class AuditOptions(BaseModel):
    doc_id: UUID
