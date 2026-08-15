# Verificação híbrida POR SEÇÃO (visual + determinística) entre um artigo e um
# template de revista. Três seções: pré-textuais (p.1), textuais (p.2 + corpo)
# e pós-textuais (referências) — rodam concorrentemente via asyncio.gather.

from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from iaEditais.features.template_abnt.template_check.bounds import (
    compute_bounds,
)
from iaEditais.features.template_abnt.template_check.constants import (
    SEC_POS,
    SEC_PRE,
    SEC_TEXT,
    SEC_TITLES,
    VISION_MODEL,
)
from iaEditais.features.template_abnt.template_check.schemas import (
    HybridReport,
    Metadata,
    SectionResult,
    build_report,
    build_section_result,
)
from iaEditais.features.template_abnt.template_check.script_runner import (
    run_script_page1,
    run_script_page2,
    run_script_references,
)
from iaEditais.features.template_abnt.template_check.visual_check import (
    run_visual_check,
)

REPORT_APPROACH = 'hybrid_visual'
REPORT_DESCRIPTION = (
    'Abordagem híbrida por seção (pré-textuais, textuais e pós-textuais): verificação '
    'visual (modelo de visão) e determinística (PyMuPDF). O scan textual agrega as '
    'páginas de corpo do artigo; o pós-textual agrega todas as páginas de referências.'
)


async def run_pre_textual_task(client: AsyncOpenAI | None, template_path: str, article_path: str,
                                tpl_page_count: int, art_page_count: int, skip_visual: bool) -> SectionResult:
    visual, script_criteria = await asyncio.gather(
        run_visual_check(client, SEC_PRE, SEC_TITLES[SEC_PRE], template_path, 1, article_path, 1, skip_visual),
        asyncio.to_thread(run_script_page1, template_path, article_path),
    )
    return build_section_result(
        SEC_PRE, SEC_TITLES[SEC_PRE],
        [1] if tpl_page_count >= 1 else [],
        [1] if art_page_count >= 1 else [],
        visual, script_criteria,
    )


async def run_textual_task(client: AsyncOpenAI | None, template_path: str, article_path: str,
                            art_bounds: dict | None, tpl_page_count: int, art_page_count: int,
                            skip_visual: bool) -> SectionResult:
    tpl_p2 = 2 if tpl_page_count >= 2 else None
    art_p2 = 2 if art_page_count >= 2 else None
    visual, (script_criteria, art_p2_pages) = await asyncio.gather(
        run_visual_check(client, SEC_TEXT, SEC_TITLES[SEC_TEXT], template_path, tpl_p2, article_path, art_p2, skip_visual),
        asyncio.to_thread(run_script_page2, template_path, article_path, art_bounds),
    )
    return build_section_result(
        SEC_TEXT, SEC_TITLES[SEC_TEXT],
        [tpl_p2] if tpl_p2 else [], art_p2_pages, visual, script_criteria,
    )


async def run_pos_textual_task(client: AsyncOpenAI | None, template_path: str, article_path: str,
                                tpl_bounds: dict | None, art_bounds: dict | None,
                                skip_visual: bool) -> SectionResult:
    tpl_ref_page = tpl_bounds['start_page'] if tpl_bounds else None
    art_ref_page = art_bounds['start_page'] if art_bounds else None
    visual, (script_criteria, tpl_ref_pages, art_ref_pages) = await asyncio.gather(
        run_visual_check(client, SEC_POS, SEC_TITLES[SEC_POS], template_path, tpl_ref_page,
                          article_path, art_ref_page, skip_visual),
        asyncio.to_thread(run_script_references, template_path, article_path, tpl_bounds, art_bounds),
    )
    return build_section_result(
        SEC_POS, SEC_TITLES[SEC_POS], tpl_ref_pages, art_ref_pages, visual, script_criteria,
    )


def build_metadata(template_path: str, article_path: str, skip_visual: bool) -> Metadata:
    return Metadata(
        approach=REPORT_APPROACH,
        model='—' if skip_visual else VISION_MODEL,
        template_file=template_path,
        article_file=article_path,
    )


# Orquestração: ponto de entrada chamado por service.py.
async def compare(template_path: str, article_path: str, skip_visual: bool = False) -> HybridReport:
    client = None if skip_visual else AsyncOpenAI()
    try:
        tpl_bounds, art_bounds, tpl_page_count, art_page_count = await asyncio.to_thread(
            compute_bounds, template_path, article_path
        )

        sec_pre, sec_text, sec_pos = await asyncio.gather(
            run_pre_textual_task(client, template_path, article_path, tpl_page_count, art_page_count, skip_visual),
            run_textual_task(client, template_path, article_path, art_bounds, tpl_page_count, art_page_count, skip_visual),
            run_pos_textual_task(client, template_path, article_path, tpl_bounds, art_bounds, skip_visual),
        )
    finally:
        if client is not None:
            await client.close()

    secoes = [sec_pre, sec_text, sec_pos]
    metadata = build_metadata(template_path, article_path, skip_visual)
    return build_report(metadata, secoes, REPORT_DESCRIPTION)
