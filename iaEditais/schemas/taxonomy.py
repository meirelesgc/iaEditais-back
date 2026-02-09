from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from iaEditais.schemas.branch import BranchPublic
from iaEditais.schemas.common import FilterPage
from iaEditais.schemas.source import SourcePublic


class TaxonomySchema(BaseModel):
    title: str
    description: str


class TaxonomyCreate(TaxonomySchema):
    typification_id: UUID
    source_ids: list[UUID]


class TaxonomyUpdate(TaxonomySchema):
    id: UUID
    typification_id: UUID
    source_ids: list[UUID]


class TaxonomyPublic(TaxonomySchema):
    id: UUID
    typification_id: UUID
    branches: list[BranchPublic]
    sources: list[SourcePublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaxonomyList(BaseModel):
    taxonomies: list[TaxonomyPublic]


class TaxonomyFilter(FilterPage):
    q: Optional[str] = None
