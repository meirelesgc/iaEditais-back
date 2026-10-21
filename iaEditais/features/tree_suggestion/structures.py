"""Estruturas da geração de sugestões: saídas estruturadas do modelo e o
contrato de entrada/saída do gerador (sem acesso ao banco).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# --- Saídas estruturadas do LLM -------------------------------------------


class ScopeDocumentType(BaseModel):
    name: str = Field(description='Nome curto do tipo documental regulado.')
    description: str = Field(description='Do que se trata esse tipo.')


class ScopeResult(BaseModel):
    source_name: str = Field(
        description='Nome oficial do documento normativo enviado.'
    )
    source_description: str = Field(
        description='Resumo em uma ou duas frases do que o documento regula.'
    )
    document_types: List[ScopeDocumentType] = Field(
        default_factory=list,
        description='Tipos documentais regulados pelo documento.',
    )


class RuleCandidate(BaseModel):
    document_type: str = Field(
        description='Nome do tipo documental, exatamente como na lista.'
    )
    taxonomy_title: str = Field(
        description='Agrupamento temático da regra (ex.: Formatação).'
    )
    taxonomy_description: str
    branch_title: str = Field(
        description='Regra verificável, curta e objetiva.'
    )
    branch_description: str = Field(
        description='O que deve ser verificado para cumprir a regra.'
    )
    quote: str = Field(
        description='Trecho LITERAL do documento que fundamenta a regra.'
    )
    rationale: str = Field(description='Por que o trecho gera essa regra.')
    rule_type: Literal['content', 'formatting'] = Field(
        description=(
            "'formatting' se a regra depende da aparência ou da posição do "
            "texto na página; 'content' se é verificável lendo o texto."
        )
    )


class RuleBatchResult(BaseModel):
    rules: List[RuleCandidate] = Field(default_factory=list)


Decision = Literal['new', 'update', 'similar', 'same']


class ConsolidatedBranch(BaseModel):
    title: str
    description: str
    candidate_ids: List[int] = Field(default_factory=list)
    decision: Decision = 'new'
    existing_id: Optional[str] = None
    rationale: str = ''


class ConsolidatedTaxonomy(BaseModel):
    title: str
    description: str
    candidate_ids: List[int] = Field(default_factory=list)
    decision: Decision = 'new'
    existing_id: Optional[str] = None
    rationale: str = ''
    branches: List[ConsolidatedBranch] = Field(default_factory=list)


class ConsolidationResult(BaseModel):
    taxonomies: List[ConsolidatedTaxonomy] = Field(default_factory=list)


# --- Contrato do gerador --------------------------------------------------


@dataclass
class ExistingBranch:
    id: UUID
    title: str
    description: Optional[str] = None


@dataclass
class ExistingTaxonomy:
    id: UUID
    title: str
    description: Optional[str] = None
    branches: List[ExistingBranch] = field(default_factory=list)


@dataclass
class ExistingTree:
    """Árvore atual relevante para a geração."""

    typification_id: Optional[UUID] = None
    typification_name: Optional[str] = None
    taxonomies: List[ExistingTaxonomy] = field(default_factory=list)
    typification_names: List[tuple[UUID, str]] = field(default_factory=list)


@dataclass
class SuggestedNode:
    key: str
    kind: str
    operation: str
    title: str
    description: Optional[str] = None
    parent_key: Optional[str] = None
    parent_entity_id: Optional[UUID] = None
    target_entity_id: Optional[UUID] = None
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    rationale: Optional[str] = None
    similar_to_id: Optional[UUID] = None
    similarity_note: Optional[str] = None


@dataclass
class GenerationResult:
    page_count: int
    model_name: str
    nodes: List[SuggestedNode] = field(default_factory=list)
    excluded_rules: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
