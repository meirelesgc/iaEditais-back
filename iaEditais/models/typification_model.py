from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CreateTypification(BaseModel):
    name: str
    source: list[UUID] = []


class Typification(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    source: list[UUID]

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
