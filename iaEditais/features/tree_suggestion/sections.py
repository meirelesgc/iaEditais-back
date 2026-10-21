"""Detecção de cabeçalhos e construção da árvore de seções do documento.

A detecção usa a tipografia das linhas (corpo de texto em tamanho base) e a
numeração hierárquica quando o documento a traz. Cabeçalhos repetidos em
todas as páginas (rodapés, números de página) são descartados.
"""

import re
import unicodedata
from typing import List, Optional, Sequence

from iaEditais.features.tree_suggestion.extraction import (
    ExtractedDocument,
    ExtractedLine,
)
from iaEditais.features.tree_suggestion.section_models import Heading, Section

NUMBERED_TITLE = re.compile(r'^(\d+(?:[.)]\d+)*)[.)]?\s+\S')
ONLY_NUMBER = re.compile(r'^[\d\s.\-–—:;/()\[\]]+$')
SENTENCE_END = ('.', ',', ';', ':', '!', '?')
MAX_HEADING_CHARS = 200
MAX_HEADING_LEVEL = 6
REPEATED_TITLE_MIN = 3
SENTENCE_MAX_CHARS = 80
HEADING_MAX_WORDS = 25
TITLE_NOISE = re.compile(r'[^0-9a-z]+')


def _normalized_title(title: str) -> str:
    decomposed = unicodedata.normalize('NFKD', title or '')
    stripped = ''.join(
        c for c in decomposed if not unicodedata.combining(c)
    )
    return TITLE_NOISE.sub(' ', stripped.casefold()).strip()


def body_font_size(lines: Sequence[ExtractedLine]) -> float:
    """Tamanho de fonte mais comum, ponderado pelo número de caracteres."""
    weights: dict[float, int] = {}
    for line in lines:
        if not line.text.strip():
            continue
        weights[line.size] = weights.get(line.size, 0) + len(line.text)
    if not weights:
        return 0.0
    return max(weights.items(), key=lambda item: item[1])[0]


def _is_heading_candidate(line: ExtractedLine, body_size: float) -> bool:
    text = line.text.strip()
    if not text or len(text) > MAX_HEADING_CHARS:
        return False
    if ONLY_NUMBER.match(text):
        return False
    if text[-1] in SENTENCE_END and len(text) > SENTENCE_MAX_CHARS:
        return False
    if len(text.split()) > HEADING_MAX_WORDS:
        return False

    larger = body_size > 0 and line.size >= body_size * 1.05
    bold_same_size = (
        line.bold and body_size > 0 and line.size >= body_size * 0.95
    )
    return larger or bold_same_size


def _numbered_level(text: str) -> Optional[int]:
    match = NUMBERED_TITLE.match(text)
    if not match:
        return None
    parts = [p for p in re.split(r'[.)]', match.group(1)) if p]
    return min(len(parts), MAX_HEADING_LEVEL)


def _detect_headings(document: ExtractedDocument) -> List[Heading]:
    body_size = body_font_size(document.lines)
    candidates = [
        line
        for line in document.lines
        if _is_heading_candidate(line, body_size)
    ]

    occurrences: dict[str, int] = {}
    for line in candidates:
        key = _normalized_title(line.text)
        occurrences[key] = occurrences.get(key, 0) + 1

    kept = [
        line
        for line in candidates
        if occurrences[_normalized_title(line.text)] < REPEATED_TITLE_MIN
    ]

    sizes = sorted({line.size for line in kept}, reverse=True)
    size_levels = {
        size: min(index + 1, MAX_HEADING_LEVEL)
        for index, size in enumerate(sizes)
    }

    headings: List[Heading] = []
    for line in kept:
        title = line.text.strip()
        level = _numbered_level(title) or size_levels.get(line.size, 1)
        headings.append(
            Heading(
                line_number=line.line_number,
                level=max(1, min(level, MAX_HEADING_LEVEL)),
                title=title,
                raw=line.text,
                page=line.page,
                char_start=line.char_start,
            )
        )
    return headings


def _section_end(
    headings: Sequence[Heading], index: int, total_chars: int
) -> int:
    level = headings[index].level
    for next_index in range(index + 1, len(headings)):
        if headings[next_index].level <= level:
            return headings[next_index].char_start or total_chars
    return total_chars


def build_section_tree(
    headings: Sequence[Heading], full_text: str
) -> List[Section]:
    """Monta a árvore de seções a partir dos cabeçalhos detectados."""
    roots: List[Section] = []
    stack: List[Section] = []
    total_chars = len(full_text)

    for index, heading in enumerate(headings):
        section = Section(
            heading=heading,
            char_start=heading.char_start,
            heading_char_start=heading.char_start,
            char_end=_section_end(headings, index, total_chars),
        )
        while stack and stack[-1].level >= heading.level:
            stack.pop()

        if stack:
            parent = stack[-1]
            section.parent_title = parent.title
            section.breadcrumb = [*parent.breadcrumb, parent.title]
            parent.children.append(section)
        else:
            roots.append(section)

        stack.append(section)

    for section in roots:
        _fill_content(section, full_text)

    return roots


def _fill_content(section: Section, full_text: str) -> None:
    start = section.char_start or 0
    end = section.char_end or len(full_text)
    section.content = full_text[start:end]
    for child in section.children:
        _fill_content(child, full_text)


def flatten_sections(sections: Sequence[Section]) -> List[Section]:
    """Lista as seções em profundidade, na ordem do documento."""
    flat: List[Section] = []

    def walk(section: Section) -> None:
        flat.append(section)
        for child in section.children:
            walk(child)

    for section in sections:
        walk(section)
    return flat


def build_sections_tree(document: ExtractedDocument) -> List[Section]:
    headings = _detect_headings(document)
    return build_section_tree(headings, document.text)
