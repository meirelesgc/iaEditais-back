# Verificação visual (modelo de visão da OpenAI) por página — assíncrona.
# Prompt em prompts/prompt_template.jinja2, renderizado via prompt_loader.

from __future__ import annotations

import asyncio
import base64

from openai import AsyncOpenAI

from iaEditais.features.template_abnt.prompt_loader import render_prompt
from iaEditais.features.template_abnt.template_check.constants import (
    REFERENCES_LABEL_HINTS,
    VISION_DETAIL,
    VISION_DPI,
    VISION_MODEL,
    VISION_REASONING_EFFORT,
    VISION_TEMPERATURE,
    VISUAL_PROMPT_TEMPLATE,
)
from iaEditais.features.template_abnt.template_check.image_utils import (
    render_page_png,
)
from iaEditais.features.template_abnt.template_check.schemas import (
    Criterion,
    VisualComparisonResult,
    VisualCriterionItem,
    make_visual_criterion,
)


def to_data_url(png_bytes: bytes) -> str:
    encoded = base64.b64encode(png_bytes).decode()
    return f'data:image/png;base64,{encoded}'


def image_block(png_bytes: bytes, detail: str = VISION_DETAIL) -> dict:
    return {'type': 'input_image', 'image_url': to_data_url(png_bytes), 'detail': detail}


def text_block(text: str) -> dict:
    return {'type': 'input_text', 'text': text}


def is_references_section(label: str) -> bool:
    lowered = label.lower()
    return any(hint in lowered for hint in REFERENCES_LABEL_HINTS)


def build_visual_prompt(label: str) -> str:
    return render_prompt(
        VISUAL_PROMPT_TEMPLATE,
        label=label,
        is_references_section=is_references_section(label),
    )


def render_page_safe(path: str, page_number: int | None, dpi: int) -> bytes | None:
    if not page_number:
        return None
    try:
        return render_page_png(path, page_number=page_number, dpi=dpi)
    except Exception:
        return None


async def visual_compare(client: AsyncOpenAI, template_png: bytes, article_png: bytes,
                          label: str) -> VisualComparisonResult:
    content = [
        text_block(f'TEMPLATE - {label}:'), image_block(template_png),
        text_block(f'ARTIGO - {label}:'), image_block(article_png),
    ]
    response = await client.responses.parse(
        model=VISION_MODEL,
        instructions=build_visual_prompt(label),
        input=[{'role': 'user', 'content': content}],
        text_format=VisualComparisonResult,
        reasoning={'effort': VISION_REASONING_EFFORT},
        temperature=VISION_TEMPERATURE,
    )
    result = response.output_parsed
    if result is None:
        raise RuntimeError('Modelo de visão não retornou uma saída estruturada (possível refusal).')
    return result


async def render_pages(template_path: str, template_page: int | None, article_path: str,
                        article_page: int | None, dpi: int) -> tuple[bytes | None, bytes | None]:
    return await asyncio.gather(
        asyncio.to_thread(render_page_safe, template_path, template_page, dpi),
        asyncio.to_thread(render_page_safe, article_path, article_page, dpi),
    )


def skipped_criterion(visual_id: str, visual_title: str) -> Criterion:
    return make_visual_criterion(
        visual_id, visual_title, True,
        [VisualCriterionItem(criterio='Verificação visual',
                             justificativa='Comparação visual não executada (--skip-visual).')],
    )


def missing_page_render_criterion(visual_id: str, visual_title: str, missing_side: str) -> Criterion:
    return make_visual_criterion(
        visual_id, visual_title, False,
        [VisualCriterionItem(
            criterio='Disponibilidade da página',
            justificativa=f'Não foi possível renderizar a página correspondente no {missing_side}.',
        )],
    )


def failed_query_criterion(visual_id: str, visual_title: str, exc: Exception) -> Criterion:
    return make_visual_criterion(
        visual_id, visual_title, False,
        [VisualCriterionItem(criterio='Consulta ao modelo de visão',
                             justificativa=f'Falha ao consultar o modelo: {exc}')],
    )


async def run_visual_check(client: AsyncOpenAI | None, section_id: str, label: str, template_path: str,
                            template_page: int | None, article_path: str, article_page: int | None,
                            skip_visual: bool) -> Criterion:
    visual_id = f'{section_id}_visual'
    visual_title = f'Verificação visual — {label}'

    if skip_visual:
        return skipped_criterion(visual_id, visual_title)

    tpl_png, art_png = await render_pages(template_path, template_page, article_path, article_page, VISION_DPI)
    if tpl_png is None or art_png is None:
        missing_side = 'template' if tpl_png is None else 'artigo'
        return missing_page_render_criterion(visual_id, visual_title, missing_side)

    try:
        result = await visual_compare(client, tpl_png, art_png, label)
    except Exception as exc:
        return failed_query_criterion(visual_id, visual_title, exc)

    return make_visual_criterion(visual_id, visual_title, result.match, result.criterios)
