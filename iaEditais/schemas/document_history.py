from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentStatus(str, Enum):
    PENDING = 'PENDING'
    UNDER_CONSTRUCTION = 'UNDER_CONSTRUCTION'
    WAITING_FOR_REVIEW = 'WAITING_FOR_REVIEW'
    COMPLETED = 'COMPLETED'


class DocumentHistorySchema(BaseModel):
    status: DocumentStatus = DocumentStatus.PENDING


class DocumentHistoryPublic(DocumentHistorySchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
