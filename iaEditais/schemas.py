from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from iaEditais.models import AccessType


class Message(BaseModel):
    message: str


class FilterPage(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1)


class UnitSchema(BaseModel):
    name: str
    location: Optional[str] = None


class UnitCreate(UnitSchema):
    pass


class UnitUpdate(UnitSchema):
    id: UUID
    pass


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
    password: str


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
