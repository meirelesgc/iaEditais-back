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


class SourceSchema(BaseModel):
    name: str
    description: str


class SourceCreate(SourceSchema):
    pass


class SourceUpdate(SourceSchema):
    id: UUID
    pass


class SourcePublic(SourceSchema):
    id: UUID

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SourceList(BaseModel):
    sources: list[SourcePublic]


class TypificationSchema(BaseModel):
    name: str


class TypificationCreate(TypificationSchema):
    source_ids: list[UUID] = []


class TypificationUpdate(TypificationSchema):
    id: UUID
    source_ids: list[UUID] = []


class TypificationPublic(TypificationSchema):
    id: UUID

    sources: list[SourcePublic] = []

    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TypificationList(BaseModel):
    typifications: list[TypificationPublic]
