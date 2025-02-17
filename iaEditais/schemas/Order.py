from pydantic import Field, BaseModel
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


class CreateOrder(BaseModel):
    name: str
    typification: list[UUID] = []


class Order(CreateOrder):
    id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class Release(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    order_id: UUID
    taxonomy: list
    created_at: datetime = Field(default_factory=datetime.now)


class DetailedOrder(Order):
    releases: list[Release]


class ReleaseFeedback(BaseModel):
    """Modelo para avaliar a conformidade de um edital com um requisito específico."""

    feedback: str = Field(
        description='Parecer detalhado sobre a conformidade do edital com o critério avaliado.'
    )
    fulfilled: bool = Field(
        description='Indica se o edital atende ao requisito especificado (True para cumprido, False para não cumprido).'
    )
