# Schema do relatório híbrido (por seção) e funções puras para construir os
# critérios/relatório a partir dos resultados dos checks determinísticos e visuais.

from __future__ import annotations

from pydantic import BaseModel


class Check(BaseModel):
    field: str
    template_value: str
    article_value: str
    match: bool


class VisualCriterionItem(BaseModel):
    criterio: str
    justificativa: str


class Criterion(BaseModel):
    id: str
    title: str
    match: bool
    is_visual: bool = False
    checks: list[Check] = []
    criterios: list[VisualCriterionItem] = []


class SectionResult(BaseModel):
    id: str
    title: str
    template_pages: list[int]
    article_pages: list[int]
    match: bool
    criteria: list[Criterion]


class Summary(BaseModel):
    is_compliant: bool
    secoes_total: int
    secoes_passed: int
    description: str


class Metadata(BaseModel):
    approach: str
    model: str
    template_file: str
    article_file: str


class HybridReport(BaseModel):
    metadata: Metadata
    summary: Summary
    secoes: list[SectionResult]


class VisualComparisonResult(BaseModel):
    match: bool
    confidence: float
    criterios: list[VisualCriterionItem]


def make_check(field: str, template: str, article: str, match: bool) -> Check:
    return Check(field=field, template_value=template, article_value=article, match=match)


def all_match(checks: list[Check]) -> bool:
    return all(c.match for c in checks) if checks else False


def make_script_criterion(cid: str, title: str, checks: list[Check]) -> Criterion:
    return Criterion(id=cid, title=title, match=all_match(checks), is_visual=False, checks=checks)


def make_visual_criterion(
    cid: str, title: str, match: bool, criterios: list[VisualCriterionItem]
) -> Criterion:
    return Criterion(id=cid, title=title, match=match, is_visual=True, criterios=criterios)


def build_section_result(
    section_id: str,
    title: str,
    template_pages: list[int],
    article_pages: list[int],
    visual_criterion: Criterion,
    script_criteria: list[Criterion],
) -> SectionResult:
    criteria = [visual_criterion, *script_criteria]
    return SectionResult(
        id=section_id,
        title=title,
        template_pages=template_pages,
        article_pages=article_pages,
        match=all(c.match for c in criteria),
        criteria=criteria,
    )


def build_summary(secoes: list[SectionResult], description: str) -> Summary:
    passed = sum(1 for s in secoes if s.match)
    return Summary(
        is_compliant=passed == len(secoes),
        secoes_total=len(secoes),
        secoes_passed=passed,
        description=description,
    )


def build_report(metadata: Metadata, secoes: list[SectionResult], description: str) -> HybridReport:
    summary = build_summary(secoes, description)
    return HybridReport(metadata=metadata, summary=summary, secoes=secoes)
