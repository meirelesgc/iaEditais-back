# Builders determinísticos de critério, operando sobre perfis de página
# (dicts retornados por pdf_metrics.extract_page_metrics/aggregate_page_metrics).
# Reaproveitados tanto para a página 1 (página única vs página única) quanto
# para a página 2 (página única vs perfil agregado de várias páginas do artigo).

from __future__ import annotations

from iaEditais.features.template_abnt.template_check.comparison import (
    families_match,
    within,
)
from iaEditais.features.template_abnt.template_check.constants import (
    FONT_SIZE_TOL_PT,
    GUTTER_TOL_MM,
    MARGIN_BOTTOM_TOL_MM,
    MARGIN_TOL_MM,
    PAGE_TOL_MM,
    PT_TO_MM,
    SPACING_TOL_MM,
)
from iaEditais.features.template_abnt.template_check.formatting import (
    fmt_bool,
    fmt_mm,
    fmt_pt,
    fmt_ratio,
)
from iaEditais.features.template_abnt.template_check.schemas import (
    Criterion,
    make_check,
    make_script_criterion,
)

MARGIN_SIDES = ('top', 'bottom', 'left', 'right')
MARGIN_LABELS = {'top': 'superior', 'bottom': 'inferior', 'left': 'esquerda', 'right': 'direita'}
MARGIN_TOLERANCES = {
    'top': MARGIN_TOL_MM,
    'bottom': MARGIN_BOTTOM_TOL_MM,
    'left': MARGIN_TOL_MM,
    'right': MARGIN_TOL_MM,
}


def build_page_size(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check('formato', tpl['page_format'], art['page_format'],
                   tpl['page_format'] == art['page_format']),
        make_check('largura', fmt_mm(tpl['width_mm']), fmt_mm(art['width_mm']),
                   within(tpl['width_mm'], art['width_mm'], PAGE_TOL_MM)),
        make_check('altura', fmt_mm(tpl['height_mm']), fmt_mm(art['height_mm']),
                   within(tpl['height_mm'], art['height_mm'], PAGE_TOL_MM)),
    ]
    return make_script_criterion('page_size', 'Tamanho da página', checks)


def build_columns(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check('numero_colunas', str(tpl['column_count']), str(art['column_count']),
                   tpl['column_count'] == art['column_count']),
        make_check('espaco_entre_colunas', fmt_mm(tpl['gutter_mm']), fmt_mm(art['gutter_mm']),
                   within(tpl['gutter_mm'], art['gutter_mm'], GUTTER_TOL_MM)),
    ]
    return make_script_criterion('columns', 'Número de colunas', checks)


def build_margins(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check(
            MARGIN_LABELS[side],
            fmt_mm(tpl['margins_mm'][side]),
            fmt_mm(art['margins_mm'][side]),
            within(tpl['margins_mm'][side], art['margins_mm'][side], MARGIN_TOLERANCES[side]),
        )
        for side in MARGIN_SIDES
    ]
    return make_script_criterion('margins', 'Margens', checks)


def build_main_font(tpl: dict, art: dict) -> Criterion:
    checks = [
        make_check('familia', tpl['font_family'], art['font_family'],
                   families_match(tpl['font_family'], art['font_family'])),
        make_check('tamanho', fmt_pt(tpl['font_size_pt']), fmt_pt(art['font_size_pt']),
                   within(tpl['font_size_pt'], art['font_size_pt'], FONT_SIZE_TOL_PT)),
        make_check('bold', fmt_bool(tpl['font_bold']), fmt_bool(art['font_bold']),
                   tpl['font_bold'] == art['font_bold']),
        make_check('cor', tpl['font_color'], art['font_color'],
                   tpl['font_color'] == art['font_color']),
    ]
    return make_script_criterion('main_font', 'Fonte principal do texto', checks)


def leading_mm(profile: dict) -> float | None:
    ratio, size = profile.get('spacing_ratio'), profile.get('font_size_pt')
    if ratio is None or not size:
        return None
    return ratio * size * PT_TO_MM


def build_line_spacing(tpl: dict, art: dict) -> Criterion:
    tpl_lead, art_lead = leading_mm(tpl), leading_mm(art)
    leading_ok = (
        tpl_lead is not None and art_lead is not None
        and within(tpl_lead, art_lead, SPACING_TOL_MM)
    )
    checks = [
        make_check('modo', tpl['spacing_mode'], art['spacing_mode'], leading_ok),
        make_check('leading', fmt_mm(tpl_lead) if tpl_lead else 'indeterminado',
                   fmt_mm(art_lead) if art_lead else 'indeterminado', leading_ok),
        make_check('razao', fmt_ratio(tpl['spacing_ratio']), fmt_ratio(art['spacing_ratio']),
                   leading_ok),
    ]
    return Criterion(id='line_spacing', title='Espaçamento entre linhas', match=leading_ok, checks=checks)


# Todos os critérios de página; a página 1 usa um subconjunto (margens
# distorcidas pela capa/instruções do template, cobertas pela verificação visual).
PAGE_BUILDERS = [build_page_size, build_columns, build_margins, build_main_font, build_line_spacing]
PAGE1_BUILDERS = [build_page_size, build_columns, build_main_font, build_line_spacing]


def build_references_typography(tpl_ref: dict | None, art_ref: dict | None) -> Criterion:
    title = 'Formatação tipográfica das referências'
    if not tpl_ref or not art_ref:
        checks = [make_check('secao_localizada', fmt_bool(bool(tpl_ref)), fmt_bool(bool(art_ref)),
                              bool(tpl_ref) == bool(art_ref))]
        return make_script_criterion('references_typography', title, checks)
    checks = [
        make_check('familia_fonte', tpl_ref['font_family'], art_ref['font_family'],
                   families_match(tpl_ref['font_family'], art_ref['font_family'])),
        make_check('tamanho_fonte', fmt_pt(tpl_ref['font_size_pt']), fmt_pt(art_ref['font_size_pt']),
                   within(tpl_ref['font_size_pt'], art_ref['font_size_pt'], FONT_SIZE_TOL_PT)),
        make_check('alinhamento', tpl_ref['text_alignment'], art_ref['text_alignment'],
                   tpl_ref['text_alignment'] == art_ref['text_alignment']),
        make_check('estilo_numeracao', tpl_ref['numbering_style'], art_ref['numbering_style'],
                   tpl_ref['numbering_style'] == art_ref['numbering_style']),
    ]
    return make_script_criterion('references_typography', title, checks)


def missing_page_criterion(cid: str, title: str) -> Criterion:
    checks = [make_check('pagina_disponivel', 'sim', 'não', False)]
    return make_script_criterion(cid, title, checks)
