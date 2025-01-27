from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from pydantic import BaseModel, Field


class CreateGuideline(BaseModel):
    title: str
    description: str = None
    source: Optional[List[UUID]] = None


class Guideline(CreateGuideline):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
