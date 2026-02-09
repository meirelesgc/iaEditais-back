from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from iaEditais.schemas.common import FilterPage


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


class UnitFilter(FilterPage):
    q: Optional[str] = None
