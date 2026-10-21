"""Etapas determinísticas da geração: unidades de texto, lotes, normalização,
localização de evidências e comparação de títulos.
"""

import difflib
import re
import unicodedata
from bisect import bisect_left
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

from iaEditais.features.tree_suggestion.section_models import Section

HYPHEN_BREAK = re.compile(r'(\w)-\s*\n\s*(\w)')
TITLE_NOISE = re.compile(r'[^0-9a-z]+')
SOFT_HYPHEN = '\u00ad'
ANCHOR_WORD_COUNTS = (6, 4, 3, 2)
MAX_ANCHOR_CANDIDATES = 200
MIN_ANCHOR_CHARS = 8
REGION_SLACK = 40


@dataclass
class TextUnit:
    """Trecho contíguo do documento (seção ou preâmbulo)."""

    title: str
    char_start: int
    char_end: int


@dataclass
class TextBatch:
    """Conjunto de unidades enviado numa única chamada ao modelo."""

    index: int
    char_start: int
    char_end: int
    text: str


@dataclass
class EvidenceMatch:
    quote: str
    pages: List[int]
    char_start: int
    char_end: int
    score: float


def build_text_units(
    full_text: str, sections: Sequence[Section]
) -> List[TextUnit]:
    """Particiona o texto pelos inícios de seção, sem sobreposição.

    O trecho anterior ao primeiro cabeçalho vira a unidade 'Preâmbulo'. Sem
    seções, o documento inteiro é uma unidade só.
    """
    starts: List[Tuple[int, str]] = []
    for sec in flatten(sections):
        start = sec.heading_char_start
        if start is None:
            start = sec.char_start
        if start is None:
            continue
        label = ' > '.join([*sec.breadcrumb, sec.title]) or sec.title
        starts.append((start, label))

    starts = sorted(dict(starts).items())
    units: List[TextUnit] = []
    first_start = starts[0][0] if starts else len(full_text)
    if full_text[:first_start].strip():
        units.append(TextUnit('Preâmbulo', 0, first_start))

    for index, (start, label) in enumerate(starts):
        end = len(full_text)
        if index + 1 < len(starts):
            end = starts[index + 1][0]
        if full_text[start:end].strip():
            units.append(TextUnit(label, start, end))

    return units


def flatten(sections: Sequence[Section]) -> List[Section]:
    """Lista as seções em profundidade, na ordem do documento."""
    flat: List[Section] = []

    def walk(section: Section) -> None:
        flat.append(section)
        for child in section.children:
            walk(child)

    for section in sections:
        walk(section)
    return flat


def build_batches(
    full_text: str, units: Sequence[TextUnit], max_chars: int
) -> List[TextBatch]:
    """Agrupa unidades consecutivas até `max_chars`.

    Uma unidade maior que o orçamento é fatiada em pedaços de no máximo
    `max_chars`.
    """
    pieces: List[TextUnit] = []
    for unit in units:
        start = unit.char_start
        while unit.char_end - start > max_chars:
            pieces.append(TextUnit(unit.title, start, start + max_chars))
            start += max_chars
        pieces.append(TextUnit(unit.title, start, unit.char_end))

    batches: List[TextBatch] = []
    current: List[TextUnit] = []

    def flush() -> None:
        if not current:
            return
        start, end = current[0].char_start, current[-1].char_end
        batches.append(
            TextBatch(len(batches), start, end, full_text[start:end])
        )
        current.clear()

    for piece in pieces:
        size = piece.char_end - piece.char_start
        if current and (piece.char_end - current[0].char_start) > max_chars:
            flush()
        current.append(piece)
        if size >= max_chars:
            flush()
    flush()
    return batches


def normalize_with_map(text: str) -> Tuple[str, List[int]]:
    """Normaliza para comparação e devolve o mapa para o texto original.

    A normalização baixa a caixa, remove marcas de hifenização e colapsa
    espaços. Para cada caractere normalizado, guarda o índice correspondente
    no texto original.
    """
    chars: List[str] = []
    index_map: List[int] = []
    index = 0
    length = len(text)
    pending_space = False

    while index < length:
        char = text[index]
        if char == '-' and index + 1 < length:
            after = index + 1
            while after < length and text[after] in ' \t':
                after += 1
            if (
                after < length
                and text[after] == '\n'
                and chars
                and chars[-1].isalnum()
            ):
                index = after + 1
                while index < length and text[index].isspace():
                    index += 1
                continue
        if char == SOFT_HYPHEN:
            index += 1
            continue
        if char.isspace():
            pending_space = bool(chars)
            index += 1
            continue
        if pending_space:
            chars.append(' ')
            index_map.append(index)
            pending_space = False
        for folded in char.casefold():
            chars.append(folded)
            index_map.append(index)
        index += 1

    return ''.join(chars), index_map


def normalize(text: str) -> str:
    return normalize_with_map(text)[0]


def offset_to_page(page_map: Sequence[Dict[str, Any]], offset: int) -> int:
    """Converte offset do texto completo em número de página (base 1)."""
    page = 0
    for entry in page_map:
        if entry.get('char_start', 0) <= offset:
            page = entry.get('page', page)
        else:
            break
    return page + 1


def pages_for_range(
    page_map: Sequence[Dict[str, Any]], start: int, end: int
) -> List[int]:
    first = offset_to_page(page_map, start)
    last = offset_to_page(page_map, max(start, end - 1))
    return list(range(first, last + 1))


def _anchor_candidates(haystack: str, needle: str) -> List[int]:
    """Posições da haystack onde começam âncoras do começo da needle."""
    words = needle.split()
    for count in ANCHOR_WORD_COUNTS:
        if len(words) < count:
            continue
        anchor = ' '.join(words[:count])
        if len(anchor) < MIN_ANCHOR_CHARS:
            continue
        positions: List[int] = []
        start = 0
        while len(positions) < MAX_ANCHOR_CANDIDATES:
            position = haystack.find(anchor, start)
            if position < 0:
                break
            positions.append(position)
            start = position + 1
        if positions:
            return positions
    return []


def _best_alignment(
    needle: str, haystack: str
) -> Tuple[float, int, int]:
    """Melhor correspondência parcial entre a needle e a haystack.

    Devolve a pontuação (0 a 100) e o intervalo encontrado na haystack.
    """
    if not needle or not haystack:
        return 0.0, 0, 0

    window = len(needle)
    best_score = 0.0
    best_start = 0
    best_end = 0

    for position in _anchor_candidates(haystack, needle):
        left = max(0, position - REGION_SLACK)
        right = min(len(haystack), position + window + REGION_SLACK)
        chunk = haystack[left:right]
        matcher = difflib.SequenceMatcher(None, needle, chunk)
        blocks = [b for b in matcher.get_matching_blocks() if b.size]
        if not blocks:
            continue
        matched = sum(block.size for block in blocks)
        region_start = blocks[0].b
        region_end = blocks[-1].b + blocks[-1].size
        region_len = region_end - region_start
        if not region_len:
            continue
        score = 100 * 2 * matched / (len(needle) + region_len)
        if score > best_score:
            best_score = score
            best_start = left + region_start
            best_end = left + region_end

    return best_score, best_start, best_end


class EvidenceLocator:
    """Localiza trechos citados pelo modelo no texto extraído."""

    def __init__(
        self,
        full_text: str,
        page_map: Sequence[Dict[str, Any]],
        min_score: float,
    ):
        self.full_text = full_text
        self.page_map = page_map
        self.min_score = min_score
        self.normalized, self.index_map = normalize_with_map(full_text)

    def _norm_range(self, start: int, end: int) -> Tuple[int, int]:
        return (
            bisect_left(self.index_map, start),
            bisect_left(self.index_map, end),
        )

    def _build(
        self, quote: str, norm_start: int, norm_end: int, score: float
    ) -> EvidenceMatch:
        start = self.index_map[norm_start]
        end = self.index_map[norm_end - 1] + 1
        return EvidenceMatch(
            quote=quote.strip(),
            pages=pages_for_range(self.page_map, start, end),
            char_start=start,
            char_end=end,
            score=score,
        )

    def locate(
        self,
        quote: str,
        hint_range: Optional[Tuple[int, int]] = None,
    ) -> Optional[EvidenceMatch]:
        """Procura o trecho de forma exata (normalizada) no documento e, se não
        encontrar, por similaridade aproximada dentro de `hint_range`."""
        needle = normalize(quote)
        if not needle:
            return None

        position = self.normalized.find(needle)
        if position >= 0:
            return self._build(quote, position, position + len(needle), 100)

        low, high = (
            self._norm_range(*hint_range)
            if hint_range
            else (0, len(self.normalized))
        )
        haystack = self.normalized[low:high]
        if not haystack:
            return None

        score, start, end = _best_alignment(needle, haystack)
        if score < self.min_score:
            return None
        return self._build(quote, low + start, low + end, score)


def normalize_title(title: str) -> str:
    """Normaliza títulos para comparação (sem acentos e pontuação)."""
    decomposed = unicodedata.normalize('NFKD', title or '')
    stripped = ''.join(c for c in decomposed if not unicodedata.combining(c))
    return TITLE_NOISE.sub(' ', stripped.casefold()).strip()


def find_similar_title(
    title: str, candidates: Iterable[Tuple[UUID, str]]
) -> Optional[Tuple[UUID, str]]:
    """Retorna a entidade cujo título normalizado é igual ao informado."""
    target = normalize_title(title)
    if not target:
        return None
    for entity_id, candidate_title in candidates:
        if normalize_title(candidate_title) == target:
            return entity_id, candidate_title
    return None
