from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from iaEditais.schemas.common import FilterPage
from iaEditais.schemas.source import SourcePublic
from iaEditais.schemas.taxonomy import TaxonomyPublic


class TypificationSchema(BaseModel):
    name: str
    document_group_id: Optional[UUID] = None
    document_group_item_id: Optional[UUID] = None


class TypificationCreate(TypificationSchema):
    source_ids: list[UUID]


class TypificationUpdate(TypificationSchema):
    id: UUID
    source_ids: list[UUID]


class TypificationClone(BaseModel):
    name: Optional[str] = None


class TypificationPublic(TypificationSchema):
    id: UUID
    sources: list[SourcePublic]
    taxonomies: list[TaxonomyPublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TypificationList(BaseModel):
    typifications: list[TypificationPublic]


class TypificationFilter(FilterPage):
    q: Optional[str] = None
