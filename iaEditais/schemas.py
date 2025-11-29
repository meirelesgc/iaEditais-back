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


class UserPublicMessage(BaseModel):
    id: UUID
    username: str

    model_config = ConfigDict(from_attributes=True)


class DocumentMessageCreate(BaseModel):
    message: str


class DocumentMessagePublic(BaseModel):
    id: UUID
    message: str
    created_at: datetime
    user: UserPublicMessage

    model_config = ConfigDict(from_attributes=True)


class DocumentHistorySchema(BaseModel):
    status: DocumentStatus = DocumentStatus.PENDING


class DocumentHistoryPublic(DocumentHistorySchema):
    id: UUID
    messages: list[DocumentMessagePublic]
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
    description: str | None
    check_tree: list[AppliedTypificationPublic]

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentReleaseList(BaseModel):
    releases: list[DocumentReleasePublic]


# ===========================
# Evaluation Schemas
# ===========================

class TestCollectionSchema(BaseModel):
    name: str
    description: Optional[str] = None


class TestCollectionCreate(TestCollectionSchema):
    pass


class TestCollectionUpdate(TestCollectionSchema):
    pass


class TestCollectionPublic(TestCollectionSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestCollectionList(BaseModel):
    test_collections: list[TestCollectionPublic]


class AIModelSchema(BaseModel):
    name: str
    code_name: str


class AIModelCreate(AIModelSchema):
    pass


class AIModelPublic(AIModelSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AIModelList(BaseModel):
    ai_models: list[AIModelPublic]


class MetricSchema(BaseModel):
    name: str
    criteria: Optional[str] = None
    evaluation_steps: Optional[str] = None
    threshold: Optional[float] = 0.5


class MetricCreate(MetricSchema):
    pass


class MetricUpdate(MetricSchema):
    pass


class MetricPublic(MetricSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MetricList(BaseModel):
    metrics: list[MetricPublic]


class TestCaseSchema(BaseModel):
    name: str
    test_collection_id: UUID
    branch_id: Optional[UUID] = None
    doc_id: UUID
    input: Optional[str] = None
    expected_feedback: Optional[str] = None
    expected_fulfilled: bool = False


class TestCaseCreate(TestCaseSchema):
    pass


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
    input: Optional[str] = None
    expected_feedback: Optional[str] = None
    expected_fulfilled: Optional[bool] = None
    branch_id: Optional[UUID] = None


class TestCasePublic(TestCaseSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestCaseList(BaseModel):
    test_cases: list[TestCasePublic]


class TestRunSchema(BaseModel):
    test_collection_id: Optional[UUID] = None
    created_by: Optional[UUID] = None


class TestRunCreate(TestRunSchema):
    pass


class TestRunExecute(BaseModel):
    test_collection_id: Optional[UUID] = None
    test_case_id: Optional[UUID] = None
    metric_ids: list[UUID]
    model_id: Optional[UUID] = None
    # If test_collection_id is provided, all cases in collection are run
    # If specific test cases are needed, we could add test_case_ids list


class TestRunExecutionResult(BaseModel):
    """Resultado da execução de um test run"""
    test_run_id: str
    case_count: int
    results: list[dict]
    
    model_config = ConfigDict(from_attributes=False)


class TestRunPublic(TestRunSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestRunList(BaseModel):
    test_runs: list[TestRunPublic]


class TestResultPublic(BaseModel):
    id: UUID
    test_run_id: UUID
    test_case_id: UUID
    metric_id: UUID
    model_id: UUID
    threshold_used: Optional[float] = None
    reason_feedback: Optional[str] = None
    score_feedback: Optional[float] = None
    passed_feedback: Optional[bool] = None
    actual_feedback: Optional[str] = None
    actual_fulfilled: Optional[bool] = None
    passed_fulfilled: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestResultList(BaseModel):
    test_results: list[TestResultPublic]
