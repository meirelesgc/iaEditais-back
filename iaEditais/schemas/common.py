from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str


class Message(BaseModel):
    message: str


class FilterPage(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(100, ge=1)
