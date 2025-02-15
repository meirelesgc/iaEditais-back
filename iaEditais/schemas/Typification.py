from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from typing import Optional
from uuid import UUID


class CreateTypification(BaseModel):
    name: str
    source: list[UUID]


class Typification(CreateTypification):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
