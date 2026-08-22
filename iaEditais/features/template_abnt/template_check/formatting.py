# Funções puras de formatação de valores para exibição nos critérios (checks).

from __future__ import annotations


def fmt_mm(value: float) -> str:
    return f'{value:.1f} mm'


def fmt_pt(value: float) -> str:
    return f'{value:.1f} pt'


def fmt_bool(value: bool) -> str:
    return 'sim' if value else 'não'


def fmt_ratio(value: float | None) -> str:
    return 'indeterminado' if value is None else f'{value:.2f}'
