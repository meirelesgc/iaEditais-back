from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from iaEditais.schemas.common import FilterPage


class BranchFilter(FilterPage):
    taxonomy_id: Optional[UUID] = None
    q: Optional[str] = None


class BranchSchema(BaseModel):
    title: str
    description: str


class BranchCreate(BranchSchema):
    taxonomy_id: UUID


class BranchUpdate(BranchSchema):
    id: UUID
    taxonomy_id: UUID


class BranchPublic(BranchSchema):
    id: UUID
    taxonomy_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BranchList(BaseModel):
    branches: list[BranchPublic]
