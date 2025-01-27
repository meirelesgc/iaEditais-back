from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
