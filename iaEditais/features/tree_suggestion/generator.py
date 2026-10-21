"""Orquestração da geração de sugestões da árvore de verificação a partir de
um PDF normativo.

Não acessa o banco: recebe a árvore existente e devolve nós sugeridos já
validados (evidência localizada e duplicatas sinalizadas).
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel

from iaEditais.core.llm import get_fast_model, get_model
from iaEditais.core.settings import Settings
from iaEditais.features.tree_suggestion.extraction import extract_document
from iaEditais.features.tree_suggestion.prompts import (
    CONSOLIDATION_PROMPT,
    RULES_PROMPT,
    SCOPE_PROMPT,
)
from iaEditais.features.tree_suggestion.sections import (
    build_sections_tree,
    flatten_sections,
)
from iaEditais.features.tree_suggestion.structures import (
    ConsolidatedBranch,
    ConsolidatedTaxonomy,
    ConsolidationResult,
    ExistingTaxonomy,
    ExistingTree,
    GenerationResult,
    RuleBatchResult,
    RuleCandidate,
    ScopeDocumentType,
    ScopeResult,
    SuggestedNode,
)
from iaEditais.features.tree_suggestion.text import (
    EvidenceLocator,
    EvidenceMatch,
    TextBatch,
    build_batches,
    build_text_units,
    find_similar_title,
    normalize,
    normalize_title,
)

logger = logging.getLogger(__name__)
SETTINGS = Settings()

OUTLINE_MAX_LINES = 200
OPENING_MAX_CHARS = 6000
MAX_EVIDENCE_PER_ITEM = 5
TYPIFICATION_EVIDENCE = 3
SIMILAR_TITLE_NOTE = 'Título equivalente a um item já existente na árvore.'


class TreeSuggestionGenerationError(Exception):
    """Falha irrecuperável na geração (mensagem exibível ao usuário)."""


def _model_name(model: BaseChatModel) -> str:
    return str(
        getattr(model, 'model_name', None)
        or getattr(model, 'model', None)
        or type(model).__name__
    )


async def _invoke_structured(model: BaseChatModel, schema, prompt: str):
    structured = model.with_structured_output(schema)
    result = await structured.ainvoke(prompt)
    if isinstance(result, dict):
        result = schema.model_validate(result)
    if not isinstance(result, schema):
        raise TreeSuggestionGenerationError(
            'O modelo de linguagem retornou uma resposta inválida.'
        )
    return result


def _extract(pdf_path: str):
    document = extract_document(pdf_path)
    sections = build_sections_tree(document)
    return document.text, document.page_map, sections


def _outline(sections) -> str:
    lines = [
        f'{"  " * max(sec.level - 1, 0)}- {sec.title}'
        for sec in flatten_sections(list(sections))
    ]
    return '\n'.join(lines[:OUTLINE_MAX_LINES]) or '(sem cabeçalhos)'


async def _run_scope(
    model: BaseChatModel, full_text: str, sections, mode: str, existing
) -> Tuple[ScopeResult, List[ScopeDocumentType]]:
    scope = await _invoke_structured(
        model,
        ScopeResult,
        SCOPE_PROMPT.format(
            outline=_outline(sections),
            opening=full_text[:OPENING_MAX_CHARS],
        ),
    )
    if mode == 'enrich':
        types = [
            ScopeDocumentType(name=existing.typification_name, description='')
        ]
    else:
        types = _unique_types(scope.document_types) or [
            ScopeDocumentType(
                name=scope.source_name,
                description=scope.source_description,
            )
        ]
    return scope, types


def _unique_types(types: Sequence[ScopeDocumentType]):
    seen = set()
    unique = []
    for doc_type in types:
        key = normalize_title(doc_type.name)
        if key and key not in seen:
            seen.add(key)
            unique.append(doc_type)
    return unique


async def _run_rules(
    model: BaseChatModel,
    batches: Sequence[TextBatch],
    types: Sequence[ScopeDocumentType],
    max_concurrency: int,
) -> Tuple[List[Tuple[RuleCandidate, TextBatch]], int]:
    semaphore = asyncio.Semaphore(max(1, max_concurrency))
    type_names = '; '.join(f'"{t.name}"' for t in types)

    async def run(batch: TextBatch):
        async with semaphore:
            return await _invoke_structured(
                model,
                RuleBatchResult,
                RULES_PROMPT.format(
                    document_types=type_names,
                    section_label=f'lote {batch.index + 1}',
                    text=batch.text,
                ),
            )

    results = await asyncio.gather(
        *(run(batch) for batch in batches), return_exceptions=True
    )
    candidates: List[Tuple[RuleCandidate, TextBatch]] = []
    failures = 0
    for batch, result in zip(batches, results):
        if isinstance(result, Exception):
            failures += 1
            logger.warning(
                'Falha na extração de regras do lote %s: %s',
                batch.index,
                result,
            )
            continue
        candidates.extend((rule, batch) for rule in result.rules)

    if batches and failures == len(batches):
        raise TreeSuggestionGenerationError(
            'Não foi possível extrair regras do documento.'
        )
    return candidates, failures


def _resolve_type(
    name: str, types: Sequence[ScopeDocumentType]
) -> Optional[str]:
    target = normalize_title(name)
    for doc_type in types:
        if normalize_title(doc_type.name) == target:
            return doc_type.name
    return types[0].name if len(types) == 1 else None


def _collect_excluded(
    candidates: Sequence[Tuple[RuleCandidate, TextBatch]],
    locator: EvidenceLocator,
) -> List[Dict[str, Any]]:
    """Regras de formatação verificadas, deduplicadas pelo trecho."""
    excluded: List[Dict[str, Any]] = []
    seen = set()
    for rule, batch in candidates:
        match = locator.locate(
            rule.quote, hint_range=(batch.char_start, batch.char_end)
        )
        if not match:
            continue
        key = normalize(match.quote)
        if key in seen:
            continue
        seen.add(key)
        excluded.append({
            'title': rule.branch_title,
            'quote': match.quote,
            'pages': match.pages,
        })
    return excluded


def _validate_evidence(
    candidates: Sequence[Tuple[RuleCandidate, TextBatch]],
    locator: EvidenceLocator,
    types: Sequence[ScopeDocumentType],
) -> Tuple[
    Dict[str, List[Tuple[int, RuleCandidate]]], Dict[int, EvidenceMatch]
]:
    by_type: Dict[str, List[Tuple[int, RuleCandidate]]] = {}
    matches: Dict[int, EvidenceMatch] = {}
    for rule, batch in candidates:
        type_name = _resolve_type(rule.document_type, types)
        if not type_name:
            continue
        match = locator.locate(
            rule.quote, hint_range=(batch.char_start, batch.char_end)
        )
        if not match:
            continue
        candidate_id = len(matches) + 1
        matches[candidate_id] = match
        by_type.setdefault(type_name, []).append((candidate_id, rule))
    return by_type, matches


def _existing_aliases(
    existing: ExistingTree,
) -> Tuple[str, Dict[str, Tuple[str, Any]]]:
    """Texto da árvore existente com apelidos curtos (T1, B1) por item."""
    aliases: Dict[str, Tuple[str, Any]] = {}
    lines = []
    branch_counter = 0
    for t_idx, taxonomy in enumerate(existing.taxonomies, start=1):
        alias = f'T{t_idx}'
        aliases[alias] = ('taxonomy', taxonomy)
        lines.append(
            f'[{alias}] {taxonomy.title} — {taxonomy.description or ""}'
        )
        for branch in taxonomy.branches:
            branch_counter += 1
            b_alias = f'B{branch_counter}'
            aliases[b_alias] = ('branch', (taxonomy, branch))
            lines.append(
                f'    [{b_alias}] {branch.title} — {branch.description or ""}'
            )
    return '\n'.join(lines) or '(vazia)', aliases


async def _run_consolidation(
    model: BaseChatModel,
    type_name: str,
    candidates: Sequence[Tuple[int, RuleCandidate]],
    existing_text: str,
) -> ConsolidationResult:
    listing = '\n'.join(
        f'{cid}: {rule.taxonomy_title} > {rule.branch_title} — '
        f'{rule.branch_description}'
        for cid, rule in candidates
    )
    return await _invoke_structured(
        model,
        ConsolidationResult,
        CONSOLIDATION_PROMPT.format(
            typification=type_name,
            candidates=listing,
            existing=existing_text,
        ),
    )


class _NodeBuilder:
    """Transforma a consolidação em nós sugeridos, com evidências."""

    def __init__(
        self,
        matches: Dict[int, EvidenceMatch],
        rules: Dict[int, RuleCandidate],
        aliases: Dict[str, Tuple[str, Any]],
    ):
        self.matches = matches
        self.rules = rules
        self.aliases = aliases
        self.nodes: List[SuggestedNode] = []
        self.counter = 0

    def _key(self, prefix: str) -> str:
        self.counter += 1
        return f'{prefix}{self.counter}'

    def evidence(self, candidate_ids: Sequence[int]) -> List[Dict[str, Any]]:
        evidence: List[Dict[str, Any]] = []
        seen = set()
        for cid in candidate_ids:
            match = self.matches.get(cid)
            if not match or match.quote in seen:
                continue
            seen.add(match.quote)
            evidence.append({'quote': match.quote, 'pages': match.pages})
        return evidence[:MAX_EVIDENCE_PER_ITEM]

    def rationale(self, text: str, candidate_ids: Sequence[int]) -> str:
        if text:
            return text
        for cid in candidate_ids:
            if cid in self.rules:
                return self.rules[cid].rationale
        return ''

    def _existing(self, alias: Optional[str], kind: str):
        found = self.aliases.get(alias or '')
        return found[1] if found and found[0] == kind else None

    def add_taxonomy(
        self,
        tax: ConsolidatedTaxonomy,
        parent_key: Optional[str],
        parent_entity_id: Optional[UUID],
        existing_taxonomies: Sequence[ExistingTaxonomy],
    ) -> None:
        branch_ids = [cid for b in tax.branches for cid in b.candidate_ids]
        all_ids = list(dict.fromkeys([*tax.candidate_ids, *branch_ids]))
        existing = self._existing(tax.existing_id, 'taxonomy')
        decision = tax.decision if existing else 'new'
        if (
            decision == 'update'
            and existing
            and tax.title == existing.title
            and tax.description == (existing.description or '')
        ):
            decision = 'same'

        tax_key: Optional[str] = None
        child_parent_entity: Optional[UUID] = None
        if decision == 'same':
            child_parent_entity = existing.id
        else:
            evidence = self.evidence(all_ids)
            if not evidence:
                return
            node = SuggestedNode(
                key=self._key('tax'),
                kind='taxonomy',
                operation='update' if decision == 'update' else 'create',
                title=tax.title,
                description=tax.description,
                parent_key=parent_key,
                parent_entity_id=None if parent_key else parent_entity_id,
                evidence=evidence,
                rationale=self.rationale(tax.rationale, all_ids),
            )
            if decision == 'update':
                node.parent_key = None
                node.parent_entity_id = None
                node.target_entity_id = existing.id
                child_parent_entity = existing.id
            else:
                tax_key = node.key
                if decision == 'similar':
                    node.similar_to_id = existing.id
                    node.similarity_note = tax.rationale or SIMILAR_TITLE_NOTE
                else:
                    _flag_similar(
                        node,
                        [(t.id, t.title) for t in existing_taxonomies],
                    )
            self.nodes.append(node)

        scope = existing if child_parent_entity else None
        for branch in _merge_branches(tax.branches):
            self.add_branch(branch, tax_key, child_parent_entity, scope)

    def add_branch(
        self,
        branch: ConsolidatedBranch,
        parent_key: Optional[str],
        parent_entity_id: Optional[UUID],
        parent_existing: Optional[ExistingTaxonomy],
    ) -> None:
        found = self._existing(branch.existing_id, 'branch')
        existing = None
        if found and parent_existing and found[0].id == parent_existing.id:
            existing = found[1]
        decision = branch.decision if existing else 'new'
        if decision == 'same' or (
            decision == 'update'
            and existing
            and branch.title == existing.title
            and branch.description == (existing.description or '')
        ):
            return

        evidence = self.evidence(branch.candidate_ids)
        if not evidence:
            return
        node = SuggestedNode(
            key=self._key('br'),
            kind='branch',
            operation='update' if decision == 'update' else 'create',
            title=branch.title,
            description=branch.description,
            parent_key=parent_key,
            parent_entity_id=None if parent_key else parent_entity_id,
            evidence=evidence,
            rationale=self.rationale(branch.rationale, branch.candidate_ids),
        )
        if decision == 'update':
            node.parent_key = None
            node.parent_entity_id = None
            node.target_entity_id = existing.id
        elif decision == 'similar':
            node.similar_to_id = existing.id
            node.similarity_note = branch.rationale or SIMILAR_TITLE_NOTE
        elif parent_existing:
            _flag_similar(
                node, [(b.id, b.title) for b in parent_existing.branches]
            )
        self.nodes.append(node)


def _flag_similar(node: SuggestedNode, scope) -> None:
    similar = find_similar_title(node.title, scope)
    if similar:
        node.similar_to_id = similar[0]
        node.similarity_note = SIMILAR_TITLE_NOTE


def _merge_branches(
    branches: Sequence[ConsolidatedBranch],
) -> List[ConsolidatedBranch]:
    merged: Dict[str, ConsolidatedBranch] = {}
    for branch in branches:
        key = normalize_title(branch.title)
        if key in merged:
            merged[key].candidate_ids.extend(branch.candidate_ids)
        else:
            merged[key] = branch.model_copy(deep=True)
    return list(merged.values())


def _merge_taxonomies(
    taxonomies: Sequence[ConsolidatedTaxonomy],
) -> List[ConsolidatedTaxonomy]:
    merged: Dict[str, ConsolidatedTaxonomy] = {}
    for taxonomy in taxonomies:
        key = normalize_title(taxonomy.title)
        if key in merged:
            merged[key].candidate_ids.extend(taxonomy.candidate_ids)
            merged[key].branches.extend(taxonomy.branches)
        else:
            merged[key] = taxonomy.model_copy(deep=True)
    return list(merged.values())


async def generate_tree_suggestions(  # noqa: PLR0913, PLR0914, PLR0917
    pdf_path: str,
    mode: str,
    existing: ExistingTree,
    model: Optional[BaseChatModel] = None,
    fast_model: Optional[BaseChatModel] = None,
    source_names: Sequence[Tuple[UUID, str]] = (),
) -> GenerationResult:
    """Gera os nós sugeridos para uma sessão.

    No modo 'enrich', `existing` deve trazer a tipificação alvo e sua
    subárvore; no modo 'create', os nomes das tipificações ativas (para
    sinalizar duplicatas).
    """
    model = model or await get_model()
    fast_model = fast_model or get_fast_model()
    stats: Dict[str, Dict[str, Any]] = {}

    full_text, page_map, sections = await asyncio.to_thread(
        _extract, pdf_path
    )
    if not full_text.strip():
        raise TreeSuggestionGenerationError(
            'O PDF não contém texto selecionável.'
        )
    units = build_text_units(full_text, sections)
    batches = build_batches(
        full_text, units, SETTINGS.TREE_SUGGESTION_BATCH_CHARS
    )
    stats['extraction'] = {
        'pages': len(page_map),
        'sections': len(units),
        'batches': len(batches),
    }

    scope, types = await _run_scope(
        fast_model, full_text, sections, mode, existing
    )
    stats['scope'] = {'document_types': [t.name for t in types]}

    candidates, failed = await _run_rules(
        model, batches, types, SETTINGS.TREE_SUGGESTION_MAX_CONCURRENCY
    )
    formatting = [c for c in candidates if c[0].rule_type == 'formatting']
    candidates = [c for c in candidates if c[0].rule_type != 'formatting']
    stats['rules'] = {
        'candidates': len(candidates) + len(formatting),
        'content': len(candidates),
        'formatting': len(formatting),
        'failed': failed,
    }

    locator = EvidenceLocator(
        full_text, page_map, SETTINGS.TREE_SUGGESTION_EVIDENCE_MIN_SCORE
    )
    by_type, matches = await asyncio.to_thread(
        _validate_evidence, candidates, locator, types
    )
    excluded_rules = await asyncio.to_thread(
        _collect_excluded, formatting, locator
    )
    stats['evidence'] = {
        'accepted': len(matches),
        'dropped': len(candidates) - len(matches),
        'excluded': len(excluded_rules),
    }

    rules = {cid: rule for group in by_type.values() for cid, rule in group}
    existing_text, aliases = _existing_aliases(existing)
    builder = _NodeBuilder(matches, rules, aliases)
    source_node = SuggestedNode(
        key='source',
        kind='source',
        operation='create',
        title=scope.source_name,
        description=scope.source_description,
    )
    _flag_similar(source_node, source_names)
    builder.nodes.append(source_node)

    for doc_type in types:
        group = by_type.get(doc_type.name)
        if not group:
            continue
        consolidated = await _run_consolidation(
            model, doc_type.name, group, existing_text
        )
        _append_type_nodes(
            builder, doc_type, group, consolidated, mode, existing
        )
    stats['consolidation'] = {'items': len(builder.nodes)}

    return GenerationResult(
        page_count=len(page_map),
        model_name=_model_name(model),
        nodes=builder.nodes,
        excluded_rules=excluded_rules,
        stats=stats,
    )


def _append_type_nodes(  # noqa: PLR0913, PLR0917
    builder: _NodeBuilder,
    doc_type: ScopeDocumentType,
    group: Sequence[Tuple[int, RuleCandidate]],
    consolidated: ConsolidationResult,
    mode: str,
    existing: ExistingTree,
) -> None:
    taxonomies = _merge_taxonomies(consolidated.taxonomies)
    if mode == 'enrich':
        for taxonomy in taxonomies:
            builder.add_taxonomy(
                taxonomy, None, existing.typification_id, existing.taxonomies
            )
        return

    start = len(builder.nodes)
    typ_node = SuggestedNode(
        key=builder._key('typ'),
        kind='typification',
        operation='create',
        title=doc_type.name,
        description=doc_type.description or None,
        evidence=builder.evidence(
            [cid for cid, _ in group][:TYPIFICATION_EVIDENCE]
        ),
        rationale='Tipo documental regulado pelo documento.',
    )
    _flag_similar(typ_node, existing.typification_names)
    builder.nodes.append(typ_node)
    for taxonomy in taxonomies:
        taxonomy.decision = 'new'
        taxonomy.existing_id = None
        builder.add_taxonomy(taxonomy, typ_node.key, None, [])

    if len(builder.nodes) == start + 1:
        builder.nodes.pop()
