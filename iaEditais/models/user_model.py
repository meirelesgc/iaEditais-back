from datetime import datetime
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class CreateUser(BaseModel):
    username: str
    email: EmailStr
    password: str | None
    unit_id: UUID | None
    phone_number: str
    access_level: Literal['DEFAULT', 'ADMIN', 'ANALYST', 'AUDITOR'] = 'DEFAULT'


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    username: str
    email: EmailStr
    unit_id: UUID | None
    phone_number: str
    access_level: Literal['DEFAULT', 'ADMIN', 'ANALYST', 'AUDITOR']
    password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class UserUpdate(BaseModel):
    username: str
    email: EmailStr
    unit_id: UUID | None
    phone_number: str
    access_level: Literal['DEFAULT', 'ADMIN', 'ANALYST', 'AUDITOR'] = 'DEFAULT'


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    unit_id: UUID | None
    phone_number: str
    access_level: Literal['DEFAULT', 'ADMIN', 'ANALYST', 'AUDITOR']
    model_config = ConfigDict(from_attributes=True)
