from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from pydantic import BaseModel, Field


class CreateTaxonomy(BaseModel):
    title: str
    description: str = None
    source: Optional[list[UUID]] = None


class Taxonomy(CreateTaxonomy):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
