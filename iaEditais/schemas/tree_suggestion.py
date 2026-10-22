from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from iaEditais.schemas.common import FilterPage


class TreeSuggestionMode(str, Enum):
    CREATE = 'create'
    ENRICH = 'enrich'


class TreeSuggestionStatus(str, Enum):
    PROCESSING = 'processing'
    READY = 'ready'
    FAILED = 'failed'
    COMPLETED = 'completed'


class TreeSuggestionItemKind(str, Enum):
    SOURCE = 'source'
    TYPIFICATION = 'typification'
    TAXONOMY = 'taxonomy'
    BRANCH = 'branch'


class TreeSuggestionItemOperation(str, Enum):
    CREATE = 'create'
    UPDATE = 'update'


class TreeSuggestionItemStatus(str, Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    DISCARDED = 'discarded'


class Evidence(BaseModel):
    quote: str
    pages: list[int] = Field(default_factory=list)


class ExcludedRule(BaseModel):
    title: str
    quote: str
    pages: list[int] = Field(default_factory=list)


class TreeSuggestionFilter(FilterPage):
    status: Optional[TreeSuggestionStatus] = None


class TreeSuggestionItemPublic(BaseModel):
    id: UUID
    session_id: UUID
    kind: TreeSuggestionItemKind
    operation: TreeSuggestionItemOperation
    status: TreeSuggestionItemStatus
    position: int
    proposed_title: str
    proposed_description: Optional[str] = None
    parent_item_id: Optional[UUID] = None
    parent_entity_id: Optional[UUID] = None
    parent_entity_title: Optional[str] = None
    target_entity_id: Optional[UUID] = None
    target_snapshot: Optional[dict[str, Any]] = None
    evidence: list[Evidence] = Field(default_factory=list)
    rationale: Optional[str] = None
    similar_to_id: Optional[UUID] = None
    similarity_note: Optional[str] = None
    final_title: Optional[str] = None
    final_description: Optional[str] = None
    applied_entity_id: Optional[UUID] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TreeSuggestionSessionPublic(BaseModel):
    id: UUID
    mode: TreeSuggestionMode
    status: TreeSuggestionStatus
    target_typification_id: Optional[UUID] = None
    target_typification_name: Optional[str] = None
    document_group_id: Optional[UUID] = None
    document_group_name: Optional[str] = None
    document_group_item_id: Optional[UUID] = None
    document_group_item_name: Optional[str] = None
    original_filename: str
    file_path: str
    page_count: Optional[int] = None
    error_message: Optional[str] = None
    generation_model: Optional[str] = None
    created_by: Optional[UUID] = None
    created_at: datetime
    processing_started_at: Optional[datetime] = None
    processing_finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TreeSuggestionSessionDetail(TreeSuggestionSessionPublic):
    items: list[TreeSuggestionItemPublic] = Field(default_factory=list)
    excluded_rules: list[ExcludedRule] = Field(default_factory=list)


class TreeSuggestionSessionList(BaseModel):
    sessions: list[TreeSuggestionSessionPublic]


class TreeSuggestionItemConfirm(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    description: Optional[str] = None
