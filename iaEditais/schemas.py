from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from iaEditais.models import AccessType, DocumentStatus


class Token(BaseModel):
    access_token: str
    token_type: str


class Message(BaseModel):
    message: str


class FilterPage(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1)


class UnitSchema(BaseModel):
    name: str
    location: Optional[str] = None


class UnitCreate(UnitSchema):
    pass


class UnitUpdate(UnitSchema):
    id: UUID


class UnitPublic(UnitSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UnitList(BaseModel):
    units: list[UnitPublic]


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    phone_number: str
    access_level: AccessType = AccessType.DEFAULT
    unit_id: Optional[UUID] = None


class UserCreate(UserSchema):
    password: str


class UserUpdate(UserSchema):
    id: UUID
    password: Optional[str] = None


class UserPublic(UserSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class SourceSchema(BaseModel):
    name: str
    description: str


class SourceCreate(SourceSchema):
    pass


class SourceUpdate(SourceSchema):
    id: UUID


class TypificationSchema(BaseModel):
    name: str


class TypificationCreate(TypificationSchema):
    source_ids: list[UUID] = []


class TypificationUpdate(TypificationSchema):
    id: UUID
    source_ids: list[UUID] = []


class TaxonomySchema(BaseModel):
    title: str
    description: str


class TaxonomyCreate(TaxonomySchema):
    typification_id: UUID


class TaxonomyUpdate(TaxonomySchema):
    id: UUID
    typification_id: UUID


class BranchSchema(BaseModel):
    title: str
    description: str


class BranchCreate(BranchSchema):
    taxonomy_id: UUID


class BranchUpdate(BranchSchema):
    id: UUID
    taxonomy_id: UUID


class SourcePublic(SourceSchema):
    id: UUID
    typifications: list[TypificationPublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TypificationPublic(TypificationSchema):
    id: UUID
    sources: list[SourcePublic] = []
    taxonomies: list[TaxonomyPublic] = []

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaxonomyPublic(TaxonomySchema):
    id: UUID
    branches: list[BranchPublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BranchPublic(BranchSchema):
    id: UUID

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SourceList(BaseModel):
    sources: list[SourcePublic]


class TypificationList(BaseModel):
    typifications: list[TypificationPublic]


class TaxonomyList(BaseModel):
    taxonomies: list[TaxonomyPublic]


class BranchList(BaseModel):
    branches: list[BranchPublic]


class DocumentHistorySchema(BaseModel):
    status: DocumentStatus = DocumentStatus.PENDING


class DocumentHistoryPublic(DocumentHistorySchema):
    id: UUID

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentSchema(BaseModel):
    name: str
    identifier: str
    description: Optional[str] = None


class DocumentCreate(DocumentSchema):
    pass


class DocumentUpdate(DocumentSchema):
    id: UUID


class DocumentPublic(DocumentSchema):
    id: UUID
    history: list[DocumentHistoryPublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    documents: list[DocumentPublic]


SourcePublic.model_rebuild()
TypificationPublic.model_rebuild()
TaxonomyPublic.model_rebuild()
