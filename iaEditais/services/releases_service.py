from typing import Optional
from uuid import UUID

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableLambda
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession as Session
from sqlalchemy.orm import selectinload

from iaEditais import prompts as PROMPTS
from iaEditais.core.dependencies import Model, VStore
from iaEditais.models import (
    AppliedBranch,
    AppliedSource,
    AppliedTaxonomy,
    AppliedTypification,
    Branch,
    DocumentRelease,
    Taxonomy,
    Typification,
)
from iaEditais.schemas import DocumentReleaseFeedback
from iaEditais.schemas.typification import TypificationList

MAX_CHUNKS = 5


def get_base_filter(db_release: DocumentRelease) -> dict:
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'
    return {'source': allowed_source}


def get_query_from_taxonomy(taxonomy: dict) -> str:
    title = (taxonomy.get('title') or '').strip()
    description = (taxonomy.get('description') or '').strip()
    if title and description:
        return f'{title}: {description}'
    return title or description


def iter_typifications(eval_args: dict):
    for typification in eval_args.get('typifications') or []:
        yield typification


def iter_taxonomies(typification: dict):
    for taxonomy in typification.get('taxonomies') or []:
        yield taxonomy


def iter_branches(taxonomy: dict):
    for branch in taxonomy.get('branches') or []:
        yield branch


def _chunk_key(chunk):
    metadata = getattr(chunk, 'metadata', None) or {}
    for k in ('id', 'chunk_id', 'uuid', 'pk'):
        if metadata.get(k) is not None:
            return f'{k}:{metadata[k]}'
    src = metadata.get('source', '')
    loc = metadata.get('loc', '')
    content = (
        getattr(chunk, 'page_content', None)
        or getattr(chunk, 'content', None)
        or ''
    )
    content = content[:80]
    return f'src:{src}|loc:{loc}|c:{content}'


async def get_branch_sessions(
    vstore: VStore,
    eval_args: dict,
    base_filter: dict,
    max_chunks: int = MAX_CHUNKS,
):
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            query = get_query_from_taxonomy(taxonomy)
            for branch in iter_branches(taxonomy):
                chunks = await vstore.asimilarity_search(
                    query, k=max_chunks, filter=base_filter
                )
                branch['sessions'] = chunks


def get_taxonomy_session_hits(eval_args: dict):
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            seen = {}
            for branch in iter_branches(taxonomy):
                for chunk in branch.get('sessions') or []:
                    seen[_chunk_key(chunk)] = chunk
            taxonomy['session_hits'] = [
                chunk.metadata.get('session') for chunk in seen.values()
            ]


async def get_documents_args(
    vstore: VStore, eval_args: dict, base_filter: dict
):
    await get_branch_sessions(vstore, eval_args, base_filter)
    get_taxonomy_session_hits(eval_args)


def get_eval_args_payload(tree: list[Typification]):
    payload = {'typifications': tree}
    return TypificationList.model_validate(payload).model_dump(mode='json')


async def get_eval_args(
    vstore: VStore, tree: list[Typification], db_release: DocumentRelease
):
    eval_args = get_eval_args_payload(tree)
    base_filter = get_base_filter(db_release)
    await get_documents_args(vstore, eval_args, base_filter)
    return eval_args


def get_chain(model: Model):
    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)
    fmt = {'format_instructions': parser.get_format_instructions()}
    prompt = PromptTemplate(
        template=PROMPTS.DOCUMENT_ANALYSIS_PROMPT,
        input_variables=[
            'document',
            'source',
            'requirement',
            'expected_session',
            'query',
        ],
        partial_variables=fmt,
    )
    return prompt | model | parser


async def apply_tree(chain: RunnableLambda, eval_args):
    last_exception = None
    for _ in range(3):
        try:
            response = await chain.abatch(eval_args)
            for item, result in zip(eval_args, response):
                item.update(result)
            return eval_args
        except Exception as e:
            last_exception = e
    raise last_exception


def _format_sources(taxonomy: dict) -> str:
    sources = taxonomy.get('sources') or []
    names = [getattr(s, 'name', str(s)) for s in sources]
    return ', '.join(names)


def _format_context(branch: dict) -> str:
    sessions = branch.get('sessions') or []
    contents = [
        getattr(d, 'page_content', getattr(d, 'content', str(d)))
        for d in sessions
    ]
    return '\n\n---\n\n'.join(contents)


def _format_requirement(branch: dict) -> str:
    title = branch.get('title', '').strip()
    desc = branch.get('description', '').strip()
    if title and desc:
        return f'{title}: {desc}'
    return title or desc


def _build_analysis_query(req_title: str, session_title: str) -> str:
    return f"Analise o item '{req_title}' na seção '{session_title}'."


def _recovery_presidio_mapping(branch: dict):
    sessions = branch.get('sessions') or []
    full_mapping = {}
    for d in sessions:
        current_mapping = d.metadata.get('presidio_mapping') or {}
        for category, entities in current_mapping.items():
            if category not in full_mapping:
                full_mapping[category] = {}
            full_mapping[category].update(entities)
    return full_mapping


def _create_eval_payload(taxonomy: dict, branch: dict) -> dict:
    expected_session = taxonomy.get('title', '').strip()
    req_title = branch.get('title', '').strip()

    return {
        'document': _format_context(branch),
        'source': _format_sources(taxonomy),
        'requirement': _format_requirement(branch),
        'expected_session': expected_session,
        'query': _build_analysis_query(req_title, expected_session),
        'presidio_mapping': _recovery_presidio_mapping(branch),
    }


async def simplify_eval_args(eval_args: dict) -> list[dict]:
    payloads = []
    for typification in iter_typifications(eval_args):
        for taxonomy in iter_taxonomies(typification):
            for branch in iter_branches(taxonomy):
                payload = _create_eval_payload(taxonomy, branch)
                if payload['document']:
                    payload['id'] = branch.get('id')
                    payloads.append(payload)

    return payloads


async def save_eval(
    session: Session,
    eval_args: list[dict],
    release_id: UUID,
    user_id: Optional[UUID] = None,
):
    applied_typs: dict[UUID, AppliedTypification] = {}
    applied_taxes: dict[UUID, AppliedTaxonomy] = {}

    for branch_data in eval_args:
        branch_id = branch_data.get('id')
        if not branch_id:
            continue

        original_branch = await session.scalar(
            select(Branch)
            .where(Branch.id == branch_id)
            .options(
                selectinload(Branch.taxonomy).selectinload(Taxonomy.sources),
                selectinload(Branch.taxonomy)
                .selectinload(Taxonomy.typification)
                .selectinload(Typification.sources),
            )
        )

        if not original_branch:
            continue

        await apply_branch_hierarchy(
            branch_data,
            session,
            original_branch,
            release_id,
            user_id,
            applied_typs,
            applied_taxes,
        )

    await session.commit()


async def _get_or_create_applied_typification(
    session: Session,
    original_typ: Typification,
    release_id: UUID,
    user_id: Optional[UUID],
    cache: dict[UUID, AppliedTypification],
) -> AppliedTypification:
    cached = cache.get(original_typ.id)
    if cached:
        return cached

    existing = await session.scalar(
        select(AppliedTypification).where(
            AppliedTypification.original_id == original_typ.id,
            AppliedTypification.applied_release_id == release_id,
        )
    )
    if existing:
        cache[original_typ.id] = existing
        return existing

    applied_typ = AppliedTypification(
        name=original_typ.name,
        applied_release_id=release_id,
        original_id=original_typ.id,
        created_by=user_id,
    )

    for src in original_typ.sources:
        applied_typ.sources.append(
            AppliedSource(
                name=src.name,
                description=src.description,
                original_id=src.id,
                created_by=user_id,
            )
        )

    session.add(applied_typ)
    await session.flush()

    cache[original_typ.id] = applied_typ
    return applied_typ


async def _get_or_create_applied_taxonomy(
    session: Session,
    original_tax: Taxonomy,
    applied_typ: AppliedTypification,
    user_id: Optional[UUID],
    cache: dict[UUID, AppliedTaxonomy],
) -> AppliedTaxonomy:
    cached = cache.get(original_tax.id)
    if cached:
        return cached

    existing = await session.scalar(
        select(AppliedTaxonomy).where(
            AppliedTaxonomy.original_id == original_tax.id,
            AppliedTaxonomy.applied_typification_id == applied_typ.id,
        )
    )
    if existing:
        cache[original_tax.id] = existing
        return existing

    applied_tax = AppliedTaxonomy(
        title=original_tax.title,
        description=original_tax.description,
        applied_typification_id=applied_typ.id,
        original_id=original_tax.id,
        created_by=user_id,
    )

    for src in original_tax.sources:
        applied_tax.sources.append(
            AppliedSource(
                name=src.name,
                description=src.description,
                original_id=src.id,
                created_by=user_id,
            )
        )

    session.add(applied_tax)
    await session.flush()

    cache[original_tax.id] = applied_tax
    return applied_tax


async def apply_branch_hierarchy(
    branch: dict,
    session: Session,
    original_branch: Branch,
    release_id: UUID,
    user_id: Optional[UUID],
    applied_typs: dict[UUID, AppliedTypification],
    applied_taxes: dict[UUID, AppliedTaxonomy],
):
    original_taxonomy = original_branch.taxonomy
    original_typification = original_taxonomy.typification

    applied_typ = await _get_or_create_applied_typification(
        session=session,
        original_typ=original_typification,
        release_id=release_id,
        user_id=user_id,
        cache=applied_typs,
    )

    applied_tax = await _get_or_create_applied_taxonomy(
        session=session,
        original_tax=original_taxonomy,
        applied_typ=applied_typ,
        user_id=user_id,
        cache=applied_taxes,
    )

    applied_branch = AppliedBranch(
        title=original_branch.title,
        description=original_branch.description,
        applied_taxonomy_id=applied_tax.id,
        original_id=original_branch.id,
        created_by=user_id,
        fulfilled=branch.get('fulfilled'),
        score=branch.get('score'),
        feedback=branch.get('feedback'),
        presidio_mapping=str(branch.get('presidio_mapping')),
    )

    session.add(applied_branch)
    await session.flush()
    return applied_branch


def _get_prompt(eval_args: list[dict]):
    sorted_data = sorted(eval_args, key=lambda x: x['score'], reverse=True)

    top_results = sorted_data[:2]
    bottom_results = sorted_data[-2:]

    top_text = ''
    for item in top_results:
        top_text += f'- Item: {item.get("query")}\n'
        top_text += f'  Nota: {item.get("score")}\n'
        top_text += f'  Status: {"Contemplado" if item.get("fulfilled") else "Não contemplado"}\n'
        top_text += f'  Feedback: {item.get("feedback")}\n\n'

    bottom_text = ''
    for item in bottom_results:
        bottom_text += f'- Item: {item.get("query")}\n'
        bottom_text += f'  Nota: {item.get("score")}\n'
        bottom_text += f'  Status: {"Contemplado" if item.get("fulfilled") else "Não contemplado"}\n'
        bottom_text += f'  Feedback: {item.get("feedback")}\n\n'

    prompt = PROMPTS.DESCRIPTION.format(
        top_text=top_text, bottom_text=bottom_text
    )
    return prompt.strip()


async def create_desc(
    session: Session, eval_args: dict, model: Model, release: DocumentRelease
):
    prompt = _get_prompt(eval_args)
    description = model.invoke(prompt)
    release.description = description.content.strip()
    await session.commit()
    await session.refresh(release)
