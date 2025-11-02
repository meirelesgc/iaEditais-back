from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceSchema(BaseModel):
    name: str
    description: str


class SourceCreate(SourceSchema):
    pass


class SourceUpdate(SourceSchema):
    id: UUID


class SourcePublic(SourceSchema):
    id: UUID
    file_path: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SourceList(BaseModel):
    sources: list[SourcePublic]
