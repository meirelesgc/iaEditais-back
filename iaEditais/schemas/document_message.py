from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from iaEditais.schemas.common import FilterPage
from iaEditais.schemas.user import UserPublic


class MessageEntityType(str, Enum):
    USER = 'USER'
    MESSAGE = 'MESSAGE'
    SOURCE = 'SOURCE'

    TYPIFICATION = 'TYPIFICATION'
    TAXONOMY = 'TAXONOMY'
    BRANCH = 'BRANCH'


class MessageMention(BaseModel):
    id: UUID = Field(validation_alias=AliasChoices('id', 'entity_id'))
    type: MessageEntityType = Field(
        validation_alias=AliasChoices('type', 'entity_type')
    )
    label: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class QuotedMessage(BaseModel):
    id: UUID
    content_preview: Optional[str] = None
    author: Optional[UserPublic] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentMessageSchema(BaseModel):
    # Conteúdo textual da mensagem, que pode conter menções e citações.
    content: str = Field()
    # Lista de entidades mencionadas na mensagem.
    mentions: Optional[List[MessageMention]] = Field(default_factory=list)
    # Mensagem citada (resposta).
    quoted_message: Optional[QuotedMessage] = Field(None)


class DocumentMessageCreate(DocumentMessageSchema):
    pass


class DocumentMessageUpdate(DocumentMessageSchema):
    id: UUID


class DocumentMessagePublic(DocumentMessageSchema):
    id: UUID
    author: UserPublic
    document_id: UUID
    release_id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentMessageList(BaseModel):
    messages: List[DocumentMessagePublic]


class MessageFilter(FilterPage):
    author_id: Optional[UUID] = None
    release_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    mention_id: Optional[UUID] = None
    mention_type: Optional[MessageEntityType] = None
