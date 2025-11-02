from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from iaEditais.schemas.source import SourcePublic
from iaEditais.schemas.taxonomy import TaxonomyPublic


class TypificationSchema(BaseModel):
    name: str


class TypificationCreate(TypificationSchema):
    source_ids: list[UUID]


class TypificationUpdate(TypificationSchema):
    id: UUID
    source_ids: list[UUID]


class TypificationPublic(TypificationSchema):
    id: UUID
    sources: list[SourcePublic]
    taxonomies: list[TaxonomyPublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TypificationList(BaseModel):
    typifications: list[TypificationPublic]
