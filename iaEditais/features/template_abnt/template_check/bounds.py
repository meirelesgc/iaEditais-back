# Localização e amostragem de páginas (template/artigo): limites da seção de
# referências e páginas candidatas ao "corpo" do artigo.

from __future__ import annotations

from iaEditais.features.template_abnt.template_check import pdf_metrics as m
from iaEditais.features.template_abnt.template_check.pdf_references import (
    find_references_bounds,
)


def first_page_bounds(bounds: dict) -> dict:
    # Restringe os limites da seção de referências à PRIMEIRA página apenas
    # (usado para o lado do template, que só entra na comparação pela 1a página).
    return {
        'start_page': bounds['start_page'],
        'start_y': bounds['start_y'],
        'end_page': bounds['start_page'],
        'end_y': None,
    }


def body_candidate_pages(doc, ref_bounds: dict | None) -> list[int]:
    # Todas as páginas do artigo, exceto a primeira e as pertencentes à seção
    # de referências (usado para o scan determinístico da página 2).
    exclude = {1}
    if ref_bounds:
        exclude |= set(range(ref_bounds['start_page'], ref_bounds['end_page'] + 1))
    candidates = [p for p in range(1, doc.page_count + 1) if p not in exclude]
    return candidates or [min(2, doc.page_count)]


def compute_bounds(template_path: str, article_path: str) -> tuple[dict | None, dict | None, int, int]:
    # Abre os dois documentos uma única vez para descobrir os limites da seção
    # de referências e a contagem de páginas; roda em thread (via asyncio.to_thread)
    # antes de disparar as 3 tarefas de página, que depois abrem seus PRÓPRIOS
    # handles de documento (PyMuPDF não é seguro para compartilhar um mesmo
    # objeto Document entre threads concorrentes).
    tpl_doc = m.open_document(template_path)
    art_doc = m.open_document(article_path)
    try:
        tpl_bounds = find_references_bounds(tpl_doc)
        art_bounds = find_references_bounds(art_doc)
        return tpl_bounds, art_bounds, tpl_doc.page_count, art_doc.page_count
    finally:
        tpl_doc.close()
        art_doc.close()
