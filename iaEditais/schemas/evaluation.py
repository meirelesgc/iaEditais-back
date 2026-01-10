"""
Schemas para o módulo de Evaluation.

Inclui schemas para TestCollection, AIModel, Metric, TestCase, TestRun e TestResult.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ===========================
# Enums
# ===========================


class TestRunStatus(str, Enum):
    """Status possíveis para um TestRun."""
    PENDING = 'PENDING'
    PROCESSING = 'PROCESSING'
    EVALUATING = 'EVALUATING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


# ===========================
# TestCollection Schemas
# ===========================


class TestCollectionSchema(BaseModel):
    name: str
    description: str


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


# ===========================
# AIModel Schemas
# ===========================


class AIModelSchema(BaseModel):
    name: str
    code_name: str


class AIModelCreate(AIModelSchema):
    pass


class AIModelUpdate(BaseModel):
    name: Optional[str] = None
    code_name: Optional[str] = None


class AIModelPublic(AIModelSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AIModelList(BaseModel):
    ai_models: list[AIModelPublic]


# ===========================
# Metric Schemas
# ===========================


class MetricSchema(BaseModel):
    name: str
    criteria: str
    evaluation_steps: str
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


# ===========================
# TestCase Schemas
# ===========================


class TestCaseSchema(BaseModel):
    name: str
    test_collection_id: UUID
    branch_id: UUID
    expected_feedback: str
    expected_fulfilled: bool


class TestCaseCreate(TestCaseSchema):
    pass


class TestCaseUpdate(BaseModel):
    name: Optional[str] = None
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


# ===========================
# TestRun Schemas
# ===========================


class TestRunSchema(BaseModel):
    test_collection_id: Optional[UUID] = None
    test_case_id: Optional[UUID] = None
    created_by: Optional[UUID] = None
    status: TestRunStatus = TestRunStatus.PENDING
    progress: Optional[str] = None
    error_message: Optional[str] = None
    release_id: Optional[UUID] = None
    doc_id: Optional[UUID] = None


class TestRunCreate(TestRunSchema):
    pass


class TestRunExecute(BaseModel):
    test_collection_id: Optional[UUID] = None
    test_case_id: Optional[UUID] = None
    metric_ids: list[UUID]
    model_id: Optional[UUID] = None


class TestRunExecutionResult(BaseModel):
    """Resultado da execução de um test run."""

    test_run_id: str
    test_collection_id: Optional[str] = None
    case_count: int
    metric_count: int
    results: list[dict]

    model_config = ConfigDict(from_attributes=False)


class TestRunPublic(TestRunSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestRunList(BaseModel):
    test_runs: list[TestRunPublic]


class TestRunAccepted(BaseModel):
    """Resposta imediata quando um test run é iniciado."""

    test_run_id: UUID
    status: str
    message: str

    model_config = ConfigDict(from_attributes=False)


# ===========================
# TestResult Schemas
# ===========================


class TestResultPublic(BaseModel):
    id: UUID
    test_run_id: UUID
    test_case_id: UUID
    metric_id: UUID
    model_id: Optional[UUID] = None
    input: Optional[str] = None
    threshold_used: Optional[float] = None
    reason_feedback: Optional[str] = None
    score_feedback: Optional[float] = None
    passed_feedback: Optional[bool] = None
    actual_feedback: Optional[str] = None
    actual_fulfilled: Optional[bool] = None
    passed_fulfilled: Optional[bool] = None
    expected_feedback: Optional[str] = None
    expected_fulfilled: Optional[bool] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestResultList(BaseModel):
    test_results: list[TestResultPublic]

