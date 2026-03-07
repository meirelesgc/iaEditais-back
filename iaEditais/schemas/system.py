from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemSettingBase(BaseModel):
    key: str
    value: Any | None = Field(default=None)
    description: Optional[str] = Field(default=None)

    model_config = ConfigDict(from_attributes=True)


class SystemSettingCreate(SystemSettingBase):
    pass


class SystemSettingUpdate(BaseModel):
    value: Any | None = Field(default=None)
    description: Optional[str] = Field(default=None)


class SystemSettingPublic(SystemSettingBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None


class SystemSettingList(BaseModel):
    settings: list[SystemSettingPublic]
