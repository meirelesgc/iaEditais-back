# Localização da seção de referências (por conteúdo, não por número de página)
# e extração das métricas tipográficas específicas dessa seção.

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from iaEditais.features.template_abnt.template_check.pdf_metrics import (
    body_font_size,
    body_spans,
    classify_spacing,
    font_is_bold,
    line_spacing_pt,
    load_page,
    primary_font_family,
    pt_to_mm,
    spacing_ratio,
    text_alignment,
)

_REFERENCES_HEADING = re.compile(
    r'^(\d+\.?\s*)?(referencias(\s+bibliograficas)?|bibliografia|references|bibliography|'
    r'works cited|literature cited)\.?$',
    re.I,
)
_SECTION_END_HEADING = re.compile(
    r'^(\d+\.?\s*)?(apendice(s)?|anexo(s)?|appendix(es)?|supplementary material)\.?$',
    re.I,
)
_BARE_NUMBER = re.compile(r'^\d+$')
_NUMBERING_PATTERNS = {
    'colchetes': re.compile(r'^\[\d+\]'),
    'numerica': re.compile(r'^\d+\.'),
    'parenteses': re.compile(r'^\(\d+\)'),
}
_HEADING_MAX_LEN = 60
_NUMBERING_STYLE_MIN_RATIO = 0.5

# LaTeX PDFs codificam acentos como letras modificadoras soltas (ex.: Referˆencias).
_LATEX_MODIFIER = re.compile(
    r'[\u02c6\u02c7\u02c8\u02ca\u02cb\u02cc\u02cd\u02ce\u02cf'
    r'\u02d8\u02d9\u02da\u02db\u02dc\u02dd\u02de\u02df'
    r'\u02e0\u02e1\u02e2\u02e3\u02e4\u02e5\u02e6\u02e7'
    r'\u02ec\u02ed\u02ee\u02ef'
    r']'
)


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', text)
    without_combining = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return _LATEX_MODIFIER.sub('', without_combining)


def line_text(line: dict) -> str:
    return ''.join(s['text'] for s in line['spans']).strip()


def find_heading_line(doc, pattern: re.Pattern, start_page: int, skip_before_y: float | None = None) -> dict | None:
    for page_number in range(start_page, doc.page_count + 1):
        page = load_page(doc, page_number)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                text = strip_accents(line_text(line))
                if not text or len(text) > _HEADING_MAX_LEN or not pattern.match(text):
                    continue
                if page_number == start_page and skip_before_y is not None and line['bbox'][1] <= skip_before_y:
                    continue
                return {'page': page_number, 'y0': line['bbox'][1], 'y1': line['bbox'][3]}
    return None


def references_start_via_toc(doc) -> int | None:
    try:
        entries = doc.get_toc()
    except Exception:
        return None
    for _level, title, page in entries:
        if _REFERENCES_HEADING.match(strip_accents(title.strip())):
            return page
    return None


def find_references_bounds(doc) -> dict | None:
    # O TOC (se existir) só restringe a página inicial da busca; a posição exata do
    # heading vem sempre da busca textual, pois a página do TOC pode conter o fim
    # de outra seção antes do título de referências.
    toc_page = references_start_via_toc(doc)
    start = find_heading_line(doc, _REFERENCES_HEADING, toc_page) if toc_page else None
    if not start:
        start = find_heading_line(doc, _REFERENCES_HEADING, 1)
    if not start:
        return None
    end = find_heading_line(doc, _SECTION_END_HEADING, start['page'], skip_before_y=start['y1'])
    return {
        'start_page': start['page'],
        'start_y': start['y1'],
        'end_page': end['page'] if end else doc.page_count,
        'end_y': end['y0'] if end else None,
    }


def references_lines(doc, bounds: dict) -> list[dict]:
    lines = []
    for page_number in range(bounds['start_page'], bounds['end_page'] + 1):
        page = load_page(doc, page_number)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                y0 = line['bbox'][1]
                if page_number == bounds['start_page'] and y0 <= bounds['start_y']:
                    continue
                if page_number == bounds['end_page'] and bounds['end_y'] is not None and y0 >= bounds['end_y']:
                    continue
                # Descarta numeração de linha de manuscrito na margem (ex: "169", "170").
                if _BARE_NUMBER.match(line_text(line)):
                    continue
                lines.append(line)
    return lines


# Agrupa as linhas por x0 (arredondado) e devolve os 2 agrupamentos mais comuns.
# Cobre tanto o recuo clássico (1a linha na base, continuação mais à direita)
# quanto o rótulo "outdentado" (número à esquerda do texto, ex: listas do MDPI).
def indent_clusters(lines: list[dict], cols: list[list[float]]) -> list[tuple[float, int]]:
    if not cols:
        return []
    left, right = cols[0]
    xs = [round(line['bbox'][0]) for line in lines if left - 2 <= line['bbox'][0] <= right]
    return Counter(xs).most_common(2)


def hanging_indent_pt(lines: list[dict], cols: list[list[float]]) -> float:
    clusters = indent_clusters(lines, cols)
    if len(clusters) < 2:
        return 0.0
    delta = abs(clusters[0][0] - clusters[1][0])
    return float(delta) if 2 < delta < 40 else 0.0


def numbering_marker_lines(lines: list[dict], cols: list[list[float]]) -> list[dict]:
    if not cols:
        return []
    left, right = cols[0]
    candidates = [line for line in lines if left - 2 <= line['bbox'][0] <= right]
    clusters = indent_clusters(lines, cols)
    if not clusters:
        return []
    marker_x = min(x for x, _ in clusters)
    return [line for line in candidates if abs(round(line['bbox'][0]) - marker_x) <= 1]


def detect_numbering_style(lines: list[dict], cols: list[list[float]]) -> str:
    markers = numbering_marker_lines(lines, cols)
    texts = [line_text(line) for line in markers]
    if not texts:
        return 'indeterminado'
    for label, pattern in _NUMBERING_PATTERNS.items():
        hits = sum(1 for t in texts if pattern.match(t))
        if hits / len(texts) >= _NUMBERING_STYLE_MIN_RATIO:
            return label
    return 'sem numeracao'


def references_pseudo_column(lines: list[dict]) -> list[list[float]]:
    if not lines:
        return []
    x0s = [line['bbox'][0] for line in lines]
    x1s = [line['bbox'][2] for line in lines]
    return [[min(x0s), max(x1s)]]


def extract_references_metrics(doc, bounds: dict | None) -> dict | None:
    if not bounds:
        return None
    lines = references_lines(doc, bounds)
    if not lines:
        return None
    spans = [s for line in lines for s in line['spans']]
    size = body_font_size(spans)
    body = body_spans(spans, size) if size else []
    cols = references_pseudo_column(lines)
    spacing = line_spacing_pt(lines, size) if size else None
    ratio = spacing_ratio(spacing, size)
    return {
        'font_family': primary_font_family(body) or 'indeterminado',
        'font_size_pt': size or 0.0,
        'font_bold': font_is_bold(body),
        'spacing_mode': classify_spacing(ratio),
        'text_alignment': text_alignment(lines, cols),
        'hanging_indent_mm': pt_to_mm(hanging_indent_pt(lines, cols)),
        'numbering_style': detect_numbering_style(lines, cols),
    }
