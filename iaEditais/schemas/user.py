from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from iaEditais.schemas.common import FilterPage


class AccessType(str, Enum):
    DEFAULT = 'DEFAULT'
    ADMIN = 'ADMIN'
    ANALYST = 'ANALYST'
    AUDITOR = 'AUDITOR'


class UserSchema(BaseModel):
    username: str
    email: EmailStr
    phone_number: str
    access_level: AccessType = AccessType.DEFAULT
    unit_id: Optional[UUID] = None


class UserCreate(UserSchema):
    password: Optional[str] = None


class UserPublic(UserSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: list[UserPublic]


class UserFilter(FilterPage):
    unit_id: Optional[UUID] = None


class UserPublicMessage(BaseModel):
    id: UUID
    username: str
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(UserSchema):
    id: UUID
    password: Optional[str] = None


class UserPublic(UserSchema):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
