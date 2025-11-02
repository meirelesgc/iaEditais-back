from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from iaEditais.schemas.branch import BranchSchema
from iaEditais.schemas.source import SourcePublic
from iaEditais.schemas.taxonomy import TaxonomySchema
from iaEditais.schemas.typification import TypificationSchema


class DocumentReleaseFeedback(BaseModel):
    feedback: str = Field(
        description=(
            'Parecer detalhado sobre a conformidade do edital com o '
            'critério avaliado.'
        )
    )
    fulfilled: bool = Field(
        description=(
            'Indica se o edital atende ao requisito especificado '
            '(True para cumprido, False para não cumprido).'
        )
    )
    score: int = Field(
        ge=0,
        le=10,
        description=(
            'Nota atribuída à conformidade do edital com o critério, '
            'variando de 0 a 10.'
        ),
    )


class AppliedBranchPublic(BranchSchema):
    id: UUID
    evaluation: DocumentReleaseFeedback

    model_config = ConfigDict(from_attributes=True)


class AppliedTaxonomyPublic(TaxonomySchema):
    id: UUID
    branches: list[AppliedBranchPublic]
    sources: list[SourcePublic]

    model_config = ConfigDict(from_attributes=True)


class AppliedTypificationPublic(TypificationSchema):
    id: UUID
    sources: list[SourcePublic]
    taxonomies: list[AppliedTaxonomyPublic]

    model_config = ConfigDict(from_attributes=True)


class DocumentReleasePublic(BaseModel):
    id: UUID
    file_path: str
    description: str | None
    check_tree: list[AppliedTypificationPublic]

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentReleaseList(BaseModel):
    releases: list[DocumentReleasePublic]
