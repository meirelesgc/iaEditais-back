from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from pydantic import BaseModel, Field


class CreateEvaluation(BaseModel):
    guideline_id: UUID
    title: str
    description: str


class Evaluation(CreateEvaluation):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
