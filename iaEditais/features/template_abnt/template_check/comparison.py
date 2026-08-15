# Predicados puros de comparação usados para decidir o "match" dos critérios.

from __future__ import annotations

from collections.abc import Iterable

# Tokens ignorados ao normalizar nomes de família de fonte para comparação.
FONT_FAMILY_IGNORED_TOKENS: Iterable[str] = ('-', '_', 'mt', 'ps', 'regular', 'roman')


def within(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def normalize_family(name: str) -> str:
    base = name.lower()
    for token in FONT_FAMILY_IGNORED_TOKENS:
        base = base.replace(token, '')
    return ''.join(ch for ch in base if ch.isalpha())


def families_match(a: str, b: str) -> bool:
    na, nb = normalize_family(a), normalize_family(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na
