from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from .typification import TypificationPublic


class BundleDocumentSchema(BaseModel):
    name: str


class BundleDocumentCreate(BundleDocumentSchema):
    typification_ids: List[UUID]


class BundleDocumentPublic(BundleDocumentSchema):
    id: UUID
    bundle_id: UUID
    typifications: List[TypificationPublic]

    model_config = ConfigDict(from_attributes=True)


class BundleSchema(BaseModel):
    name: str


class BundleCreate(BundleSchema):
    documents: List[BundleDocumentCreate]


class BundleUpdate(BaseModel):
    id: UUID
    name: Optional[str] = None
    documents: Optional[List[BundleDocumentCreate]] = None


class BundlePublic(BundleSchema):
    id: UUID
    documents: List[BundleDocumentPublic]

    model_config = ConfigDict(from_attributes=True)


class BundleFilter(BaseModel):
    q: Optional[str] = None
    offset: int = 0
    limit: int = 100


class BundleList(BaseModel):
    bundles: List[BundlePublic]


class BundleGenerateDocsRequest(BaseModel):
    base_name: str
    base_identifier: str
    base_description: str
