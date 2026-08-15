# Funções pequenas e puras para extrair métricas de formatação de UMA página
# de PDF (geometria, tipografia, colunas, espaçamento, numeração). Cada função
# faz uma única coisa; extract_page_metrics/aggregate_page_metrics orquestram.

from __future__ import annotations

import re
from collections import Counter
from statistics import median

import pymupdf

PT_PER_INCH = 72.0
MM_PER_INCH = 25.4

# Bits de estilo em span["flags"] do PyMuPDF.
FLAG_ITALIC = 1 << 1  # 2
FLAG_BOLD = 1 << 4  # 16

_PAGE_NUM_PATTERNS = [
    re.compile(r'^\d+$'),
    re.compile(r'^(p\.?|página|page)\s*\d+$', re.I),
    re.compile(r'^\d+\s*(/|of|de)\s*\d+$', re.I),
    re.compile(r'^[ivxlcdm]+$', re.I),
]


# Conversões e utilidades numéricas
def pt_to_mm(value_pt: float) -> float:
    return value_pt * MM_PER_INCH / PT_PER_INCH


def is_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


# Acesso ao documento / página
def open_document(path: str):
    return pymupdf.open(path)


def load_page(doc, page_number: int):  # page_number é 1-indexed
    return doc[page_number - 1]


def page_size_pt(page) -> tuple[float, float]:
    return page.rect.width, page.rect.height


def detect_page_format(width_mm: float, height_mm: float, tol: float = 6.0) -> str:
    if is_close(width_mm, 210.0, tol) and is_close(height_mm, 297.0, tol):
        return 'A4'
    if is_close(width_mm, 215.9, tol) and is_close(height_mm, 279.4, tol):
        return 'Letter'
    return 'Desconhecido'


# Spans de texto
def iter_spans(page) -> list[dict]:
    data = page.get_text('dict')
    spans = []
    for block in data['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                spans.append(span)
    return spans


def body_font_size(spans: list[dict]) -> float | None:
    # Pondera pela quantidade de caracteres (o corpo de texto domina o volume).
    weights: Counter = Counter()
    for s in spans:
        text = s['text'].strip()
        if text:
            weights[round(s['size'], 1)] += len(text)
    if not weights:
        return None
    return weights.most_common(1)[0][0]


def body_spans(spans: list[dict], size: float) -> list[dict]:
    return [s for s in spans if round(s['size'], 1) == size and s['text'].strip()]


# Fonte principal: família, estilo e cor
def clean_font_name(name: str) -> str:
    # Remove o prefixo de subconjunto embutido (ex: "GSIQQF+STIXGeneral").
    if '+' in name:
        name = name.split('+', 1)[1]
    return name


def primary_font_family(body: list[dict]) -> str | None:
    names = [clean_font_name(s['font']) for s in body]
    if not names:
        return None
    return Counter(names).most_common(1)[0][0]


def font_is_bold(body: list[dict]) -> bool:
    if not body:
        return False
    bold = sum(1 for s in body if (s['flags'] & FLAG_BOLD) or 'bold' in s['font'].lower())
    return bold > len(body) / 2


def font_is_italic(body: list[dict]) -> bool:
    if not body:
        return False
    italic = sum(1 for s in body if (s['flags'] & FLAG_ITALIC) or 'italic' in s['font'].lower())
    return italic > len(body) / 2


def int_to_hex_color(color_int: int) -> str:
    return '#{:06X}'.format(color_int & 0xFFFFFF)


def dominant_color(body: list[dict]) -> str | None:
    if not body:
        return None
    colors = [s.get('color', 0) for s in body]
    return int_to_hex_color(Counter(colors).most_common(1)[0][0])


# Margens
def text_blocks(page) -> list[dict]:
    return [b for b in page.get_text('dict')['blocks'] if 'lines' in b]


def text_bbox(page) -> tuple[float, float, float, float] | None:
    blocks = text_blocks(page)
    if not blocks:
        return None
    x0 = min(b['bbox'][0] for b in blocks)
    y0 = min(b['bbox'][1] for b in blocks)
    x1 = max(b['bbox'][2] for b in blocks)
    y1 = max(b['bbox'][3] for b in blocks)
    return x0, y0, x1, y1


def margins_mm(page) -> dict | None:
    width, height = page_size_pt(page)
    bbox = text_bbox(page)
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    return {
        'left': pt_to_mm(x0),
        'right': pt_to_mm(width - x1),
        'top': pt_to_mm(y0),
        'bottom': pt_to_mm(height - y1),
    }


# Linhas do corpo de texto (para colunas, alinhamento, recuo, espaçamento)
def body_lines(page, size: float) -> list[dict]:
    data = page.get_text('dict')
    lines = []
    for block in data['blocks']:
        for line in block.get('lines', []):
            line_sizes = [round(s['size'], 1) for s in line['spans'] if s['text'].strip()]
            if not line_sizes:
                continue
            if Counter(line_sizes).most_common(1)[0][0] == size:
                lines.append(line)
    return lines


# Colunas (detecção por cobertura horizontal das linhas)
def line_x_ranges(lines: list[dict]) -> list[tuple[float, float]]:
    return [(line['bbox'][0], line['bbox'][2]) for line in lines]


def merge_intervals(ranges: list[tuple[float, float]], gap: float) -> list[list[float]]:
    if not ranges:
        return []
    ordered = sorted(ranges)
    merged = [list(ordered[0])]
    for x0, x1 in ordered[1:]:
        if x0 <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], x1)
        else:
            merged.append([x0, x1])
    return merged


def detect_columns(page, lines: list[dict]) -> list[list[float]]:
    width, _ = page_size_pt(page)
    merged = merge_intervals(line_x_ranges(lines), gap=10.0)
    # Descarta faixas estreitas (linhas avulsas centralizadas, números etc.).
    return [m for m in merged if (m[1] - m[0]) >= 0.15 * width]


def column_count(cols: list[list[float]]) -> int:
    return len(cols)


def column_widths_mm(cols: list[list[float]]) -> list[float]:
    return [pt_to_mm(c[1] - c[0]) for c in cols]


def gutter_mm(cols: list[list[float]]) -> float:
    if len(cols) < 2:
        return 0.0
    ordered = sorted(cols)
    gaps = [ordered[i + 1][0] - ordered[i][1] for i in range(len(ordered) - 1)]
    return pt_to_mm(sum(gaps) / len(gaps))


# Espaçamento entre linhas
def line_spacing_pt(lines: list[dict], size: float) -> float | None:
    tops = sorted(line['bbox'][1] for line in lines)
    diffs = [round(b - a, 1) for a, b in zip(tops, tops[1:]) if 0 < (b - a) < size * 3]
    if not diffs:
        return None
    return Counter(diffs).most_common(1)[0][0]


def spacing_ratio(spacing: float | None, size: float | None) -> float | None:
    if not spacing or not size:
        return None
    return spacing / size


def classify_spacing(ratio: float | None) -> str:
    if ratio is None:
        return 'indeterminado'
    targets = {'simples': 1.0, '1.15': 1.15, '1.5': 1.5, 'duplo': 2.0}
    return min(targets.items(), key=lambda kv: abs(kv[1] - ratio))[0]


# Recuo da primeira linha do parágrafo
def first_line_indent_pt(lines: list[dict], cols: list[list[float]]) -> float:
    indents = []
    for left, right in cols:
        col_lines = [line for line in lines if left - 2 <= line['bbox'][0] <= right]
        xs = [round(line['bbox'][0]) for line in col_lines]
        if not xs:
            continue
        base = Counter(xs).most_common(1)[0][0]
        deltas = [round(x - base) for x in xs if 2 < (x - base) < 40]
        if deltas:
            indents.append(Counter(deltas).most_common(1)[0][0])
    if not indents:
        return 0.0
    return float(Counter(indents).most_common(1)[0][0])


# Alinhamento do texto
def text_alignment(lines: list[dict], cols: list[list[float]]) -> str:
    justified = 0
    centered = 0
    counted = 0
    for left, right in cols:
        span = right - left
        if span <= 0:
            continue
        col_lines = [
            line for line in lines
            if left - 2 <= line['bbox'][0] and line['bbox'][2] <= right + 2
        ]
        for line in col_lines:
            lx0, _, lx1, _ = line['bbox']
            counted += 1
            left_gap = lx0 - left
            right_gap = right - lx1
            if right_gap <= 0.03 * span:
                justified += 1
            elif abs(left_gap - right_gap) <= 0.02 * span and left_gap > 0.05 * span:
                centered += 1
    if counted == 0:
        return 'indeterminado'
    if justified / counted >= 0.6:
        return 'justificado'
    if centered / counted >= 0.4:
        return 'centralizado'
    return 'esquerda'


# Numeração de páginas
def is_page_number_text(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > 20:
        return False
    return any(p.match(t) for p in _PAGE_NUM_PATTERNS)


def numbering_format(text: str) -> str:
    if re.search(r'\d', text):
        return 'arábico'
    return 'romano'


def numbering_horizontal(x_center: float, width: float) -> str:
    if x_center < width / 3:
        return 'esquerda'
    if x_center > 2 * width / 3:
        return 'direita'
    return 'centro'


def page_numbering(page) -> dict:
    width, height = page_size_pt(page)
    data = page.get_text('dict')
    for block in data['blocks']:
        for line in block.get('lines', []):
            text = ''.join(s['text'] for s in line['spans']).strip()
            if not is_page_number_text(text):
                continue
            x0, y0, x1, y1 = line['bbox']
            vertical = 'rodapé' if y0 > height * 0.85 else ('cabeçalho' if y1 < height * 0.15 else 'corpo')
            if vertical == 'corpo':
                continue
            horizontal = numbering_horizontal((x0 + x1) / 2, width)
            return {
                'exists': True,
                'position': f'{vertical}-{horizontal}',
                'format': numbering_format(text),
            }
    return {'exists': False, 'position': 'nenhuma', 'format': 'nenhum'}


# Agregação entre páginas (robustez contra páginas atípicas)
def most_common(values: list) -> object:
    return Counter(values).most_common(1)[0][0]


def median_columns(lists: list[list[float]]) -> list[float]:
    non_empty = [values for values in lists if values]
    if not non_empty:
        return []
    length = most_common([len(values) for values in non_empty])
    same_length = [values for values in non_empty if len(values) == length]
    return [median(values[i] for values in same_length) for i in range(length)]


def numbering_key(entry: dict) -> tuple:
    return entry['exists'], entry['position'], entry['format']


def aggregate_numbering(entries: list[dict]) -> dict:
    exists, position, fmt = most_common([numbering_key(e) for e in entries])
    return {'exists': exists, 'position': position, 'format': fmt}


def aggregate_page_metrics(pages: list[dict]) -> dict:
    if len(pages) == 1:
        return pages[0]
    modal_columns = most_common([p['column_count'] for p in pages])
    same_columns = [p for p in pages if p['column_count'] == modal_columns]
    ratios = [p['spacing_ratio'] for p in pages if p['spacing_ratio'] is not None]
    return {
        'page_format': most_common([p['page_format'] for p in pages]),
        'width_mm': median(p['width_mm'] for p in pages),
        'height_mm': median(p['height_mm'] for p in pages),
        'column_count': modal_columns,
        'column_widths_mm': median_columns([p['column_widths_mm'] for p in same_columns]),
        'gutter_mm': median(p['gutter_mm'] for p in same_columns),
        'margins_mm': {
            side: median(p['margins_mm'][side] for p in pages)
            for side in ('left', 'right', 'top', 'bottom')
        },
        'font_family': most_common([p['font_family'] for p in pages]),
        'font_size_pt': median(p['font_size_pt'] for p in pages),
        'font_bold': most_common([p['font_bold'] for p in pages]),
        'font_italic': most_common([p['font_italic'] for p in pages]),
        'font_color': most_common([p['font_color'] for p in pages]),
        'spacing_ratio': median(ratios) if ratios else None,
        'spacing_mode': most_common([p['spacing_mode'] for p in pages]),
        'first_line_indent_mm': median(p['first_line_indent_mm'] for p in pages),
        'text_alignment': most_common([p['text_alignment'] for p in pages]),
        'page_numbering': aggregate_numbering([p['page_numbering'] for p in pages]),
    }


# Extrai TODAS as métricas de UMA página em um dict simples (usa um doc já aberto)
def extract_page_metrics(doc, page_number: int) -> dict:
    page = load_page(doc, page_number)
    width_pt, height_pt = page_size_pt(page)
    width_mm, height_mm = pt_to_mm(width_pt), pt_to_mm(height_pt)

    spans = iter_spans(page)
    size = body_font_size(spans)
    body = body_spans(spans, size) if size else []
    lines = body_lines(page, size) if size else []
    cols = detect_columns(page, lines)

    spacing = line_spacing_pt(lines, size) if size else None
    ratio = spacing_ratio(spacing, size)

    return {
        'page_format': detect_page_format(width_mm, height_mm),
        'width_mm': width_mm,
        'height_mm': height_mm,
        'column_count': column_count(cols),
        'column_widths_mm': column_widths_mm(cols),
        'gutter_mm': gutter_mm(cols),
        'margins_mm': margins_mm(page) or {'left': 0, 'right': 0, 'top': 0, 'bottom': 0},
        'font_family': primary_font_family(body) or 'indeterminado',
        'font_size_pt': size or 0.0,
        'font_bold': font_is_bold(body),
        'font_italic': font_is_italic(body),
        'font_color': dominant_color(body) or '#000000',
        'spacing_ratio': ratio,
        'spacing_mode': classify_spacing(ratio),
        'first_line_indent_mm': pt_to_mm(first_line_indent_pt(lines, cols)),
        'text_alignment': text_alignment(lines, cols),
        'page_numbering': page_numbering(page),
    }
