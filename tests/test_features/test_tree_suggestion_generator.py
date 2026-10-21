from pathlib import Path
from uuid import uuid4

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from iaEditais.features.tree_suggestion.generator import (
    generate_tree_suggestions,
)
from iaEditais.features.tree_suggestion.structures import (
    ConsolidatedBranch,
    ConsolidatedTaxonomy,
    ConsolidationResult,
    ExistingBranch,
    ExistingTaxonomy,
    ExistingTree,
    RuleBatchResult,
    ScopeResult,
)

RULES = [
    {
        'document_type': 'Edital de Pregao Eletronico',
        'taxonomy_title': 'Objeto',
        'taxonomy_description': 'Descricao do objeto',
        'branch_title': 'Prazo de entrega',
        'branch_description': 'Verificar o prazo de entrega',
        'quote': 'entrega em ate 30 dias',
        'rationale': 'O prazo de entrega e verificavel no texto.',
        'rule_type': 'content',
    },
    {
        'document_type': 'Edital de Pregao Eletronico',
        'taxonomy_title': 'Formatacao',
        'taxonomy_description': 'Regras de apresentacao',
        'branch_title': 'Titulo em negrito',
        'branch_description': 'Verificar o uso de negrito',
        'quote': '1. OBJETO',
        'rationale': 'Depende da apresentacao do texto.',
        'rule_type': 'formatting',
    },
]


class _FakeStructured:
    def __init__(self, schema, payload):
        self.schema = schema
        self.payload = payload

    async def ainvoke(self, prompt, *args, **kwargs):
        return self.schema.model_validate(self.payload)


class _FakeModel:
    model_name = 'fake-model'

    def __init__(self, payloads: dict):
        self.payloads = payloads

    def with_structured_output(self, schema, **kwargs):
        return _FakeStructured(schema, self.payloads[schema])


def _model() -> _FakeModel:
    return _FakeModel({
        ScopeResult: {
            'source_name': 'Edital de Pregao Eletronico 1/2026',
            'source_description': 'Documento que regula um pregao eletronico.',
            'document_types': [
                {
                    'name': 'Edital de Pregao Eletronico',
                    'description': 'Edital de licitacao',
                }
            ],
        },
        RuleBatchResult: {'rules': RULES},
        ConsolidationResult: {
            'taxonomies': [
                {
                    'title': 'Objeto',
                    'description': 'Descricao do objeto',
                    'candidate_ids': [1],
                    'decision': 'new',
                    'branches': [
                        {
                            'title': 'Prazo de entrega',
                            'description': 'Verificar o prazo de entrega',
                            'candidate_ids': [1],
                            'decision': 'new',
                        }
                    ],
                }
            ]
        },
    })


@pytest.fixture
def pdf_path(tmp_path) -> Path:
    path = tmp_path / 'edital.pdf'
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(60, height - 80, '1. OBJETO')
    pdf.setFont('Helvetica', 10)
    pdf.drawString(
        60,
        height - 110,
        'Registro de precos para o fornecimento de reagentes, com entrega',
    )
    pdf.drawString(60, height - 125, 'em ate 30 dias.')
    pdf.save()
    return path


@pytest.mark.asyncio
async def test_generate_tree_suggestions_in_create_mode(pdf_path):
    fake = _model()

    result = await generate_tree_suggestions(
        str(pdf_path),
        'create',
        ExistingTree(),
        model=fake,
        fast_model=fake,
    )

    kinds = [node.kind for node in result.nodes]
    assert kinds == ['source', 'typification', 'taxonomy', 'branch']

    source = result.nodes[0]
    assert source.title == 'Edital de Pregao Eletronico 1/2026'

    typification = result.nodes[1]
    assert typification.title == 'Edital de Pregao Eletronico'
    assert typification.evidence

    taxonomy = result.nodes[2]
    assert taxonomy.title == 'Objeto'
    assert taxonomy.parent_key == typification.key
    assert taxonomy.evidence[0]['quote'] == 'entrega em ate 30 dias'
    assert taxonomy.evidence[0]['pages'] == [1]

    branch = result.nodes[3]
    assert branch.title == 'Prazo de entrega'
    assert branch.parent_key == taxonomy.key

    assert result.page_count == 1
    assert result.excluded_rules
    assert result.excluded_rules[0]['title'] == 'Titulo em negrito'
    assert result.excluded_rules[0]['pages'] == [1]
    assert result.stats['evidence']['accepted'] == 1
    assert result.stats['evidence']['excluded'] == 1


@pytest.mark.asyncio
async def test_generate_tree_suggestions_in_enrich_mode(pdf_path):
    fake = _model()
    typification_id = uuid4()
    taxonomy_id = uuid4()
    branch_id = uuid4()
    existing = ExistingTree(
        typification_id=typification_id,
        typification_name='Edital de Pregao Eletronico',
        taxonomies=[
            ExistingTaxonomy(
                id=taxonomy_id,
                title='Objeto',
                description='Descricao do objeto',
                branches=[
                    ExistingBranch(
                        id=branch_id,
                        title='Prazo de entrega',
                        description='Verificar o prazo de entrega',
                    )
                ],
            )
        ],
    )

    result = await generate_tree_suggestions(
        str(pdf_path),
        'enrich',
        existing,
        model=fake,
        fast_model=fake,
    )

    assert [node.kind for node in result.nodes] == [
        'source',
        'taxonomy',
        'branch',
    ]

    taxonomy = result.nodes[1]
    assert taxonomy.parent_entity_id == typification_id
    assert taxonomy.parent_key is None

    branch = result.nodes[2]
    assert branch.parent_key == taxonomy.key


@pytest.mark.asyncio
async def test_generate_tree_suggestions_drops_rule_without_evidence(pdf_path):
    fake = _model()
    fake.payloads[RuleBatchResult] = {
        'rules': [
            {
                **RULES[0],
                'quote': 'trecho que nao existe no documento',
            }
        ]
    }

    result = await generate_tree_suggestions(
        str(pdf_path),
        'create',
        ExistingTree(),
        model=fake,
        fast_model=fake,
    )

    assert [node.kind for node in result.nodes] == ['source']
    assert result.stats['evidence']['dropped'] == 1
    assert result.stats['evidence']['accepted'] == 0


@pytest.mark.asyncio
async def test_generate_tree_suggestions_reuses_existing_items(pdf_path):
    fake = _model()
    taxonomy_id = uuid4()
    branch_id = uuid4()
    existing = ExistingTree(
        typification_id=uuid4(),
        typification_name='Edital de Pregao Eletronico',
        taxonomies=[
            ExistingTaxonomy(
                id=taxonomy_id,
                title='Objeto',
                description='Descricao do objeto',
                branches=[
                    ExistingBranch(
                        id=branch_id,
                        title='Prazo de entrega',
                        description='Verificar o prazo de entrega',
                    )
                ],
            )
        ],
    )
    fake.payloads[ConsolidationResult] = {
        'taxonomies': [
            ConsolidatedTaxonomy(
                title='Objeto',
                description='Descricao do objeto',
                candidate_ids=[1],
                decision='same',
                existing_id='T1',
                branches=[
                    ConsolidatedBranch(
                        title='Prazo de entrega',
                        description='Verificar o prazo de entrega',
                        candidate_ids=[1],
                        decision='same',
                        existing_id='B1',
                    )
                ],
            ).model_dump()
        ]
    }

    result = await generate_tree_suggestions(
        str(pdf_path),
        'enrich',
        existing,
        model=fake,
        fast_model=fake,
    )

    assert [node.kind for node in result.nodes] == ['source']
