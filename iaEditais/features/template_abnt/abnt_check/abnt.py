# Verificação ABNT via engenharia de prompt (somente IA), com foco em elementos
# textuais/estruturais/citações/referências. Prompt em prompts/prompt_abnt.jinja2.

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from iaEditais.features.template_abnt.abnt_check.schemas import (
    EXPECTED_BRANCH_COUNT,
    AbntAiBody,
    AbntCriterionItem,
    AbntMetadata,
    AbntReport,
    build_report,
    flatten_ai_body,
)
from iaEditais.features.template_abnt.prompt_loader import render_prompt

# gpt-5.4 aceita temperature só com reasoning.effort='none'; os dois no
# mínimo aumentam o determinismo e evitam o erro 400 da API.
AI_MODEL = 'gpt-5.4'
REASONING_EFFORT = 'none'
TEMPERATURE = 0
PROMPT_TEMPLATE = 'prompt_abnt.jinja2'
AUDIT_INSTRUCTION = (
    'Audite este documento ramo a ramo, na ordem da taxonomia das instruções. '
    'Cada ramo é obrigatório na saída.'
)


def upload_pdf(client: OpenAI, path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    uploaded = client.files.create(file=open(file_path, 'rb'), purpose='user_data')
    return uploaded.id


def build_input(article_id: str) -> list[dict]:
    return [
        {
            'role': 'user',
            'content': [
                {'type': 'input_file', 'file_id': article_id},
                {'type': 'input_text', 'text': AUDIT_INSTRUCTION},
            ],
        }
    ]


def request_criteria(article_path: str) -> list[AbntCriterionItem]:
    client = OpenAI()
    article_id = upload_pdf(client, article_path)

    response = client.responses.parse(
        model=AI_MODEL,
        instructions=render_prompt(PROMPT_TEMPLATE),
        input=build_input(article_id),
        text_format=AbntAiBody,
        reasoning={'effort': REASONING_EFFORT},
        temperature=TEMPERATURE,
    )
    body = response.output_parsed
    if body is None:
        raise RuntimeError(
            'Modelo não retornou saída estruturada (possível refusal).',
        )
    criterios = flatten_ai_body(body)
    if len(criterios) != EXPECTED_BRANCH_COUNT:
        raise RuntimeError(
            f'Esperados {EXPECTED_BRANCH_COUNT} ramos, '
            f'recebidos {len(criterios)}.',
        )
    return criterios


def build_description(model: str, criterios: list[AbntCriterionItem]) -> str:
    return (
        f'Auditoria via engenharia de prompt (IA, modelo {model}), focada em elementos textuais, '
        f'estruturais, citações e referências ABNT. Os {len(criterios)} critérios correspondem '
        f'aos ramos obrigatórios da taxonomia de estrutura e formatação.'
    )


# Orquestração: ponto de entrada chamado por service.py.
def compare(article_path: str) -> AbntReport:
    criterios = request_criteria(article_path)
    metadata = AbntMetadata(approach='abnt', model=AI_MODEL, article_file=article_path)
    description = build_description(AI_MODEL, criterios)
    return build_report(metadata, criterios, description)
