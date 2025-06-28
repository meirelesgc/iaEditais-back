from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CreateSource(BaseModel):
    name: str
    description: str


class Source(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str

    has_file: bool = False

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class SourceUpdate(CreateSource):
    id: UUID


class SourceResponse(Source):
    pass
