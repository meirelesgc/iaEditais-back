"""Extração do texto de um PDF, com mapa de páginas e metadados de linha.

O texto extraído é o mesmo usado para montar o prompt e para localizar a
evidência citada pelo modelo: cada página conhece o intervalo de caracteres
que ocupa no texto completo.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pymupdf

NULL_BYTES = re.compile(r'\x00')
SPACES = re.compile(r'[ \t]+')
PAGE_SEPARATOR = '\n\n'


@dataclass
class ExtractedLine:
    """Linha de texto com a tipografia usada para detectar cabeçalhos."""

    text: str
    page: int
    line_number: int
    char_start: int
    size: float
    bold: bool


@dataclass
class ExtractedDocument:
    """Documento extraído: texto corrido, mapa de páginas e linhas."""

    text: str
    page_map: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[ExtractedLine] = field(default_factory=list)


def _is_bold(span: Dict[str, Any]) -> bool:
    font = str(span.get('font', '')).lower()
    if 'bold' in font or 'black' in font or 'heavy' in font:
        return True
    return bool(span.get('flags', 0) & 2 ** 4)


def _line_text(line: Dict[str, Any]) -> str:
    spans = line.get('spans', [])
    return ''.join(span.get('text', '') for span in spans)


def _line_size(line: Dict[str, Any]) -> float:
    sizes = [
        float(span.get('size', 0))
        for span in line.get('spans', [])
        if span.get('text', '').strip()
    ]
    return max(sizes) if sizes else 0.0


def _line_bold(line: Dict[str, Any]) -> bool:
    spans = [s for s in line.get('spans', []) if s.get('text', '').strip()]
    if not spans:
        return False
    return any(_is_bold(span) for span in spans)


def _clean(text: str) -> str:
    return SPACES.sub(' ', NULL_BYTES.sub('', text)).rstrip()


def extract_document(pdf_path: str) -> ExtractedDocument:
    """Extrai o texto do PDF, o mapa de páginas e as linhas tipografadas."""
    parts: List[str] = []
    page_map: List[Dict[str, Any]] = []
    lines: List[ExtractedLine] = []
    char_cursor = 0
    line_number = 0

    with pymupdf.open(pdf_path) as doc:
        for page_index, page in enumerate(doc):
            if page_index:
                parts.append(PAGE_SEPARATOR)
                char_cursor += len(PAGE_SEPARATOR)

            page_text_parts: List[str] = []
            page_char_start = char_cursor

            for block in page.get_text('dict').get('blocks', []):
                for line in block.get('lines', []):
                    raw = _line_text(line)
                    cleaned = _clean(raw)
                    if not cleaned.strip():
                        continue
                    offset_in_page = sum(
                        len(part) + 1 for part in page_text_parts
                    )
                    page_text_parts.append(cleaned)
                    lines.append(
                        ExtractedLine(
                            text=cleaned,
                            page=page_index,
                            line_number=line_number,
                            char_start=page_char_start + offset_in_page,
                            size=_line_size(line),
                            bold=_line_bold(line),
                        )
                    )
                    line_number += 1

            page_text = '\n'.join(page_text_parts)
            page_map.append({
                'page': page_index,
                'char_start': page_char_start,
                'char_end': page_char_start + len(page_text),
                'char_count': len(page_text),
            })
            parts.append(page_text)
            char_cursor += len(page_text)

    return ExtractedDocument(
        text=''.join(parts), page_map=page_map, lines=lines
    )
