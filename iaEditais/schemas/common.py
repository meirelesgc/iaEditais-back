from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SortBy(str, Enum):
    CREATED_AT = 'created_at'
    UPDATED_AT = 'updated_at'


class SortOrder(str, Enum):
    ASC = 'asc'
    DESC = 'desc'


class Token(BaseModel):
    access_token: str
    token_type: str


class Message(BaseModel):
    message: str


class FilterPage(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1)


class WSMessage(BaseModel):
    event: str
    message: str
    payload: Optional[dict]
