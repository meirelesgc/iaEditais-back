# Verificação determinística por página (orquestração dos builders de critério).
# Cada função abre e fecha seus PRÓPRIOS handles de documento (thread-safe,
# pois roda em paralelo com as demais páginas via asyncio.to_thread).

from __future__ import annotations

from iaEditais.features.template_abnt.template_check import pdf_metrics as m
from iaEditais.features.template_abnt.template_check.bounds import (
    body_candidate_pages,
    first_page_bounds,
)
from iaEditais.features.template_abnt.template_check.deterministic_checks import (
    PAGE1_BUILDERS,
    PAGE_BUILDERS,
    build_references_typography,
    missing_page_criterion,
)
from iaEditais.features.template_abnt.template_check.pdf_references import (
    extract_references_metrics,
)
from iaEditais.features.template_abnt.template_check.schemas import Criterion


def run_script_page1(template_path: str, article_path: str) -> list[Criterion]:
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        if tpl_doc.page_count < 1 or art_doc.page_count < 1:
            return [missing_page_criterion('page_1_scan', 'Scan determinístico - Página 1')]
        tpl = m.extract_page_metrics(tpl_doc, 1)
        art = m.extract_page_metrics(art_doc, 1)
        return [build(tpl, art) for build in PAGE1_BUILDERS]
    finally:
        tpl_doc.close()
        art_doc.close()


def run_script_page2(template_path: str, article_path: str,
                      art_bounds: dict | None) -> tuple[list[Criterion], list[int]]:
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        if tpl_doc.page_count < 2:
            return [missing_page_criterion('page_2_scan', 'Scan determinístico - Página 2')], []
        if art_doc.page_count < 2:
            return [missing_page_criterion('page_2_scan', 'Scan determinístico - Página 2')], []
        tpl = m.extract_page_metrics(tpl_doc, 2)
        candidate_pages = body_candidate_pages(art_doc, art_bounds)
        art = m.aggregate_page_metrics([m.extract_page_metrics(art_doc, p) for p in candidate_pages])
        criteria = [build(tpl, art) for build in PAGE_BUILDERS]
        return criteria, candidate_pages
    finally:
        tpl_doc.close()
        art_doc.close()


def run_script_references(template_path: str, article_path: str, tpl_bounds: dict | None,
                           art_bounds: dict | None) -> tuple[list[Criterion], list[int], list[int]]:
    tpl_pages = [tpl_bounds['start_page']] if tpl_bounds else []
    art_pages = list(range(art_bounds['start_page'], art_bounds['end_page'] + 1)) if art_bounds else []
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        tpl_ref = extract_references_metrics(tpl_doc, first_page_bounds(tpl_bounds)) if tpl_bounds else None
        art_ref = extract_references_metrics(art_doc, art_bounds) if art_bounds else None
    finally:
        tpl_doc.close()
        art_doc.close()
    return [build_references_typography(tpl_ref, art_ref)], tpl_pages, art_pages
