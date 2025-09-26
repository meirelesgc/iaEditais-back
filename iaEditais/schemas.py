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


class UserFilter(FilterPage):
    unit_id: Optional[UUID] = None


class BranchFilter(FilterPage):
    taxonomy_id: Optional[UUID] = None


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
    password: Optional[str] = None


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


class SourcePublic(SourceSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SourceList(BaseModel):
    sources: list[SourcePublic]


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
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BranchList(BaseModel):
    branches: list[BranchPublic]


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
    branches: list[BranchPublic]
    sources: list[SourcePublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TaxonomyList(BaseModel):
    taxonomies: list[TaxonomyPublic]


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


class DocumentSchema(BaseModel):
    name: str
    identifier: str
    description: Optional[str] = None


class DocumentCreate(DocumentSchema):
    typification_ids: Optional[list[UUID]]
    editors_ids: Optional[list[UUID]]


class DocumentUpdate(DocumentSchema):
    id: UUID
    typification_ids: Optional[list[UUID]]
    editors_ids: Optional[list[UUID]]


class DocumentHistorySchema(BaseModel):
    status: DocumentStatus = DocumentStatus.PENDING


class DocumentHistoryPublic(DocumentHistorySchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentPublic(DocumentSchema):
    id: UUID
    history: list[DocumentHistoryPublic]
    typifications: list[TypificationPublic]
    editors: list[UserPublic]

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentList(BaseModel):
    documents: list[DocumentPublic]


class DocumentReleaseFeedback(BaseModel):
    feedback: str = Field(
        description=(
            'Parecer detalhado sobre a conformidade do edital com o '
            'critério avaliado.'
        )
    )
    fulfilled: bool = Field(
        description=(
            'Indica se o edital atende ao requisito especificado '
            '(True para cumprido, False para não cumprido).'
        )
    )
    score: int = Field(
        ge=0,
        le=10,
        description=(
            'Nota atribuída à conformidade do edital com o critério, '
            'variando de 0 a 10.'
        ),
    )


class AppliedBranchPublic(BranchSchema):
    id: UUID
    evaluation: DocumentReleaseFeedback

    model_config = ConfigDict(from_attributes=True)


class AppliedTaxonomyPublic(TaxonomySchema):
    id: UUID
    branches: list[AppliedBranchPublic]
    sources: list[SourcePublic]

    model_config = ConfigDict(from_attributes=True)


class AppliedTypificationPublic(TypificationSchema):
    id: UUID
    sources: list[SourcePublic]
    taxonomies: list[AppliedTaxonomyPublic]

    model_config = ConfigDict(from_attributes=True)


class DocumentReleasePublic(BaseModel):
    id: UUID
    file_path: str
    check_tree: list[AppliedTypificationPublic]

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentReleaseList(BaseModel):
    releases: list[DocumentReleasePublic]
