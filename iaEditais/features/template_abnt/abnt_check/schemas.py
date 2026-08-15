# Schema ABNT: corpo estruturado da IA (ramos obrigatórios) e relatório plano
# usado pelos endpoints. O flatten converte o objeto da API na lista do front.

from __future__ import annotations

from pydantic import BaseModel, Field


class AbntBranchResult(BaseModel):
    norma: str = Field(min_length=1)
    justificativa: str = Field(min_length=1)
    match: bool


class ElementosPreTextuais(BaseModel):
    capa: AbntBranchResult = Field(description='Capa')
    folha_de_rosto: AbntBranchResult = Field(description='Folha de rosto')
    natureza_do_trabalho: AbntBranchResult = Field(
        description='Natureza do trabalho',
    )
    resumo: AbntBranchResult = Field(description='Resumo')
    abstract: AbntBranchResult = Field(description='Abstract')
    palavras_chave: AbntBranchResult = Field(description='Palavras-chave')
    sumario: AbntBranchResult = Field(description='Sumário')


class Citacoes(BaseModel):
    citacao_direta_curta: AbntBranchResult = Field(
        description='Citação direta curta',
    )
    citacao_direta_longa: AbntBranchResult = Field(
        description='Citação direta longa',
    )
    citacao_indireta: AbntBranchResult = Field(description='Citação indireta')
    sistema_de_chamada: AbntBranchResult = Field(
        description='Sistema de chamada',
    )
    indicacao_da_fonte: AbntBranchResult = Field(
        description='Indicação da fonte',
    )


class ReferenciasBibliograficas(BaseModel):
    estrutura_das_referencias: AbntBranchResult = Field(
        description='Estrutura das referências',
    )
    padronizacao: AbntBranchResult = Field(description='Padronização')
    ordenacao: AbntBranchResult = Field(description='Ordenação')
    correspondencia: AbntBranchResult = Field(description='Correspondência')


class Ilustracoes(BaseModel):
    identificacao: AbntBranchResult = Field(description='Identificação')
    numeracao: AbntBranchResult = Field(description='Numeração')
    legenda: AbntBranchResult = Field(description='Legenda')
    fonte: AbntBranchResult = Field(description='Fonte')
    tipografia: AbntBranchResult = Field(description='Tipografia')


class Paginacao(BaseModel):
    contagem_das_paginas: AbntBranchResult = Field(
        description='Contagem das páginas',
    )
    exibicao_da_numeracao: AbntBranchResult = Field(
        description='Exibição da numeração',
    )
    posicionamento: AbntBranchResult = Field(description='Posicionamento')
    formatacao: AbntBranchResult = Field(description='Formatação')


class Resumo(BaseModel):
    conteudo: AbntBranchResult = Field(description='Conteúdo')
    extensao: AbntBranchResult = Field(description='Extensão')
    paragrafo_unico: AbntBranchResult = Field(description='Parágrafo único')
    palavras_chave: AbntBranchResult = Field(description='Palavras-chave')


class NumeracaoProgressivaDasSecoes(BaseModel):
    estrutura_hierarquica: AbntBranchResult = Field(
        description='Estrutura hierárquica',
    )
    numeracao_progressiva: AbntBranchResult = Field(
        description='Numeração progressiva',
    )
    correspondencia_entre_titulos_e_numeracao: AbntBranchResult = Field(
        description='Correspondência entre títulos e numeração',
    )
    padronizacao_dos_titulos: AbntBranchResult = Field(
        description='Padronização dos títulos',
    )
    consistencia_da_hierarquia: AbntBranchResult = Field(
        description='Consistência da hierarquia',
    )


class Sumario(BaseModel):
    presenca_do_sumario: AbntBranchResult = Field(
        description='Presença do sumário',
    )
    correspondencia_estrutural: AbntBranchResult = Field(
        description='Correspondência estrutural',
    )
    numeracao_das_secoes: AbntBranchResult = Field(
        description='Numeração das seções',
    )
    indicacao_das_paginas: AbntBranchResult = Field(
        description='Indicação das páginas',
    )
    ordem_das_secoes: AbntBranchResult = Field(description='Ordem das seções')
    padronizacao_visual: AbntBranchResult = Field(
        description='Padronização visual',
    )


class AbntAiBody(BaseModel):
    elementos_pre_textuais: ElementosPreTextuais
    citacoes: Citacoes
    referencias_bibliograficas: ReferenciasBibliograficas
    ilustracoes: Ilustracoes
    paginacao: Paginacao
    resumo: Resumo
    numeracao_progressiva_das_secoes: NumeracaoProgressivaDasSecoes
    sumario: Sumario


# (grupo, campo, rótulo do relatório). A ordem é a da taxonomia do prompt.
BRANCH_ORDER: tuple[tuple[str, str, str], ...] = (
    ('elementos_pre_textuais', 'capa', 'Capa'),
    ('elementos_pre_textuais', 'folha_de_rosto', 'Folha de rosto'),
    ('elementos_pre_textuais', 'natureza_do_trabalho', 'Natureza do trabalho'),
    ('elementos_pre_textuais', 'resumo', 'Resumo'),
    ('elementos_pre_textuais', 'abstract', 'Abstract'),
    ('elementos_pre_textuais', 'palavras_chave', 'Palavras-chave'),
    ('elementos_pre_textuais', 'sumario', 'Sumário'),
    ('citacoes', 'citacao_direta_curta', 'Citação direta curta'),
    ('citacoes', 'citacao_direta_longa', 'Citação direta longa'),
    ('citacoes', 'citacao_indireta', 'Citação indireta'),
    ('citacoes', 'sistema_de_chamada', 'Sistema de chamada'),
    ('citacoes', 'indicacao_da_fonte', 'Indicação da fonte'),
    (
        'referencias_bibliograficas',
        'estrutura_das_referencias',
        'Estrutura das referências',
    ),
    ('referencias_bibliograficas', 'padronizacao', 'Padronização'),
    ('referencias_bibliograficas', 'ordenacao', 'Ordenação'),
    ('referencias_bibliograficas', 'correspondencia', 'Correspondência'),
    ('ilustracoes', 'identificacao', 'Identificação'),
    ('ilustracoes', 'numeracao', 'Numeração'),
    ('ilustracoes', 'legenda', 'Legenda'),
    ('ilustracoes', 'fonte', 'Fonte'),
    ('ilustracoes', 'tipografia', 'Tipografia'),
    ('paginacao', 'contagem_das_paginas', 'Contagem das páginas'),
    ('paginacao', 'exibicao_da_numeracao', 'Exibição da numeração'),
    ('paginacao', 'posicionamento', 'Posicionamento'),
    ('paginacao', 'formatacao', 'Formatação'),
    ('resumo', 'conteudo', 'Conteúdo'),
    ('resumo', 'extensao', 'Extensão'),
    ('resumo', 'paragrafo_unico', 'Parágrafo único'),
    ('resumo', 'palavras_chave', 'Palavras-chave'),
    (
        'numeracao_progressiva_das_secoes',
        'estrutura_hierarquica',
        'Estrutura hierárquica',
    ),
    (
        'numeracao_progressiva_das_secoes',
        'numeracao_progressiva',
        'Numeração progressiva',
    ),
    (
        'numeracao_progressiva_das_secoes',
        'correspondencia_entre_titulos_e_numeracao',
        'Correspondência entre títulos e numeração',
    ),
    (
        'numeracao_progressiva_das_secoes',
        'padronizacao_dos_titulos',
        'Padronização dos títulos',
    ),
    (
        'numeracao_progressiva_das_secoes',
        'consistencia_da_hierarquia',
        'Consistência da hierarquia',
    ),
    ('sumario', 'presenca_do_sumario', 'Presença do sumário'),
    ('sumario', 'correspondencia_estrutural', 'Correspondência estrutural'),
    ('sumario', 'numeracao_das_secoes', 'Numeração das seções'),
    ('sumario', 'indicacao_das_paginas', 'Indicação das páginas'),
    ('sumario', 'ordem_das_secoes', 'Ordem das seções'),
    ('sumario', 'padronizacao_visual', 'Padronização visual'),
)

EXPECTED_BRANCH_COUNT = len(BRANCH_ORDER)


class AbntCriterionItem(BaseModel):
    criterio: str
    norma: str
    justificativa: str
    match: bool


class AbntSummary(BaseModel):
    is_compliant: bool
    criterios_total: int
    criterios_passed: int
    description: str


class AbntMetadata(BaseModel):
    approach: str
    model: str
    article_file: str


class AbntReport(BaseModel):
    metadata: AbntMetadata
    summary: AbntSummary
    criterios: list[AbntCriterionItem]


def flatten_ai_body(body: AbntAiBody) -> list[AbntCriterionItem]:
    items: list[AbntCriterionItem] = []
    for group_name, field_name, label in BRANCH_ORDER:
        group = getattr(body, group_name)
        result = getattr(group, field_name)
        items.append(
            AbntCriterionItem(
                criterio=label,
                norma=result.norma,
                justificativa=result.justificativa,
                match=result.match,
            )
        )
    return items


def count_passed(criterios: list[AbntCriterionItem]) -> int:
    return sum(1 for c in criterios if c.match)


def build_summary(
    criterios: list[AbntCriterionItem],
    description: str,
) -> AbntSummary:
    passed = count_passed(criterios)
    return AbntSummary(
        is_compliant=bool(criterios) and passed == len(criterios),
        criterios_total=len(criterios),
        criterios_passed=passed,
        description=description,
    )


def build_report(
    metadata: AbntMetadata,
    criterios: list[AbntCriterionItem],
    description: str,
) -> AbntReport:
    summary = build_summary(criterios, description)
    return AbntReport(
        metadata=metadata,
        summary=summary,
        criterios=criterios,
    )
