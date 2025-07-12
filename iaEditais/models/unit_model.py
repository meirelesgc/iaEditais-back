from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CreateUnit(BaseModel):
    name: str
    location: str | None = None


class Unit(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    location: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None


class UnitResponse(BaseModel):
    id: UUID
    name: str
    location: str | None = None

    class Config:
        from_attributes = True
