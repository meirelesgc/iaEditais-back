import re
import unicodedata
from collections import defaultdict
from typing import Any, Dict, List
from uuid import UUID

from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais import prompts as PROMPTS
from iaEditais.core.dependencies import Model, VStore
from iaEditais.models import DocumentMessage, DocumentRelease
from iaEditais.repositories import doc_repo
from iaEditais.schemas import DocumentMessageCreate
from iaEditais.schemas.ai import AnswerWithCitations, Citation
from iaEditais.services import (
    branch_service,
    release_logic_service,
    release_service,
)

MAX_CHUNKS = 10
BRANCH_MATCH_LIMIT = 2
BRANCH_CHUNKS_PER_MATCH = 4
FALLBACK_REFERENCES_LIMIT = 3
SNIPPET_MAX_CHARS = 120
CONTEXT_PATTERN = re.compile(r'<([^:]+):([^>]+)>')


def get_base_filter(db_release: DocumentRelease) -> dict:
    path = db_release.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'
    return {'source': allowed_source}


async def build_branch_prompt(session: AsyncSession, branch_id: str) -> str:
    branch = await branch_service.get_branch_by_id(session, branch_id)
    return f"""
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
**Item Avaliado:** {branch.taxonomy.typification.name}
**Tópico de Referência:** {branch.taxonomy.title}
**Pergunta de Verificação:** O conteúdo necessário está presente **nos trechos recuperados** e cumpre integralmente o requisitos baseados em:
{branch.title}
{branch.description}
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
"""


async def get_context(session: AsyncSession, msg: str) -> List[str]:
    matches = CONTEXT_PATTERN.findall(msg)
    context = []

    for match_type, match_id in matches:
        if match_type == 'branch':
            prompt = await build_branch_prompt(session, match_id)
            context.append(prompt)
        elif match_type != 'ai':
            print(f'Unknown type: {match_type}')

    return context


def build_chunk_prompts(chunks: List) -> List[str]:
    prompts_list = []

    for chunk in chunks:
        chunk_id = chunk.metadata.get('chunk_id', 'unknown_id')
        section = chunk.metadata.get('section_title', '')
        conteudo = chunk.page_content

        if '\n\n' in conteudo and conteudo.startswith('SECTION:'):
            conteudo = conteudo.split('\n\n', 1)[1]

        prompt = (
            f'[FONTE] chunk_id: {chunk_id}\n'
            f'SECTION: {section}\n'
            f'{conteudo.strip()}'
        )
        prompts_list.append(prompt)

    return prompts_list


async def get_prompt_context(
    vstore: VStore, db_release: DocumentRelease, msg: str
) -> tuple[List[str], List[Any]]:
    if not msg:
        return [], []

    base_filter = get_base_filter(db_release)
    original_chunks = await vstore.asimilarity_search(
        msg, k=MAX_CHUNKS, filter=base_filter
    )

    if not original_chunks:
        return [], []

    expanded_chunks = await release_logic_service.get_expanded_chunks(
        vstore, original_chunks
    )

    return build_chunk_prompts(expanded_chunks), expanded_chunks


def build_chat_prompt(recent_messages: list[Any]) -> str:
    return '\n---\n'.join([
        f"""
QUEM FALOU:
{m.author.username}:
O QUE FALOU:
{m.content}
"""
        for m in recent_messages
    ])


async def get_document_auto_context(
    session: AsyncSession, doc_id: UUID
) -> tuple[List[str], List[dict]]:
    doc = await doc_repo.get_by_id(session, doc_id)
    if not doc or doc.deleted_at:
        return [], []

    prompts_list = []
    branches: List[dict] = []
    for typification in doc.typifications:
        if typification.deleted_at:
            continue
        for taxonomy in typification.taxonomies:
            if taxonomy.deleted_at:
                continue
            for branch in taxonomy.branches:
                if branch.deleted_at:
                    continue
                branches.append({
                    'taxonomy': taxonomy.title,
                    'title': branch.title,
                    'description': branch.description,
                })
                prompt = f"""
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
**Item Avaliado:** {typification.name}
**Tópico de Referência:** {taxonomy.title}
**Pergunta de Verificação:** O conteúdo necessário está presente **nos trechos recuperados** e cumpre integralmente o requisitos baseados em:
{branch.title}
{branch.description}
<CONTEXTO-BASE-CONHECIMENTO-BRANCH:{branch.id}>
"""
                prompts_list.append(prompt)
    return prompts_list, branches


def _tokens(text: str) -> set:
    normalized = unicodedata.normalize('NFKD', (text or '').lower())
    flat = ''.join(c for c in normalized if not unicodedata.combining(c))
    return set(re.findall(r'[a-z0-9]{4,}', flat))


def _dedupe_chunks(chunks: List[Any]) -> List[Any]:
    seen = set()
    unique = []
    for chunk in chunks:
        chunk_id = chunk.metadata.get('chunk_id')
        if chunk_id and chunk_id in seen:
            continue
        if chunk_id:
            seen.add(chunk_id)
        unique.append(chunk)
    return unique


async def get_branch_targeted_context(
    vstore: VStore, db_release: DocumentRelease, msg: str,
    branches: List[dict], extra_text: str = '',
) -> tuple[List[str], List[Any]]:
    """Busca extra estilo análise: quando a pergunta (ou o histórico
    recente da conversa) cita palavras do título de um ramo, recupera
    trechos com a query estruturada '{título}: {descrição}' e expande
    para os vizinhos, como a análise faz."""
    match_tokens = _tokens(msg) | _tokens(extra_text)
    scored = []
    for branch in branches:
        overlap = match_tokens & _tokens(branch['title'])
        if overlap:
            scored.append((len(overlap), branch))
    scored.sort(key=lambda item: -item[0])
    selected = [branch for _, branch in scored[:BRANCH_MATCH_LIMIT]]

    if not selected:
        print('[chat] busca direcionada: nenhum ramo casou com a pergunta')
        return [], []

    base_filter = get_base_filter(db_release)
    matched_chunks: List[Any] = []
    for branch in selected:
        query = PROMPTS.QUERY.format(
            section=branch['taxonomy'],
            query=f"{branch['title']}: {branch['description']}",
        )
        found = await vstore.asimilarity_search(
            query, k=BRANCH_CHUNKS_PER_MATCH, filter=base_filter
        )
        print(
            f"[chat] busca direcionada '{branch['title']}': "
            f'{len(found)} chunks'
        )
        matched_chunks.extend(found)

    expanded_chunks = await release_logic_service.get_expanded_chunks(
        vstore, matched_chunks
    )
    combined = _dedupe_chunks(matched_chunks + expanded_chunks)
    print(f'[chat] busca direcionada total (com vizinhos): {len(combined)}')
    return build_chunk_prompts(combined), combined


def resolve_citations(
    citations: List[Citation], retrieved_chunks: List[Any]
) -> List[Dict]:
    resolved = []
    chunk_map = {
        chunk.metadata.get('chunk_id'): chunk.metadata
        for chunk in retrieved_chunks
        if chunk.metadata.get('chunk_id')
    }

    seen = set()
    for citation in citations:
        if citation.chunk_id in seen:
            continue

        if citation.chunk_id in chunk_map:
            meta = chunk_map[citation.chunk_id]
            raw_rects = meta.get('rects', [])
            mapped_rects = []
            for r in raw_rects:
                if len(r) == 4:
                    mapped_rects.append({
                        'x1': r[0],
                        'y1': r[1],
                        'x2': r[2],
                        'y2': r[3],
                    })

            resolved.append({
                'chunk_id': citation.chunk_id,
                'text_snippet': citation.text_snippet,
                'page': meta.get('page'),
                'rects': mapped_rects,
            })
            seen.add(citation.chunk_id)

    return resolved


def _fallback_references(chunks: List[Any]) -> List[Dict]:
    references = []
    seen = set()
    for chunk in chunks:
        chunk_id = chunk.metadata.get('chunk_id')
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)

        content = chunk.page_content or ''
        if content.startswith('SECTION:') and '\n\n' in content:
            content = content.split('\n\n', 1)[1]
        snippet = ' '.join(content.split())[:SNIPPET_MAX_CHARS]

        rects = [
            {'x1': r[0], 'y1': r[1], 'x2': r[2], 'y2': r[3]}
            for r in chunk.metadata.get('rects') or []
            if len(r) == 4
        ]
        references.append({
            'chunk_id': chunk_id,
            'text_snippet': snippet,
            'page': chunk.metadata.get('page'),
            'rects': rects,
        })
        if len(references) >= FALLBACK_REFERENCES_LIMIT:
            break
    return references


async def create_ai_response(
    session: AsyncSession,
    user_id: UUID,
    doc_id: UUID,
    data: DocumentMessageCreate,
    model: Model,
    vstore: VStore,
    recent_messages: list[DocumentMessage],
) -> Dict:
    releases_list = await release_service.get_releases_by_document(
        session, doc_id
    )
    if not releases_list:
        return {
            'answer': 'Nenhum processamento encontrado para este documento.',
            'references': [],
        }
    db_release = await release_service.get_release_with_details(
        session, releases_list[0].id
    )

    auto_prompts, doc_branches = await get_document_auto_context(
        session, doc_id
    )
    explicit_prompts = await get_context(session, data.content)
    chat_context = build_chat_prompt(recent_messages)

    branch_context, branch_chunks = await get_prompt_context(
        vstore, db_release, '\n---\n'.join(explicit_prompts)
    )

    msg_context, msg_chunks = await get_prompt_context(
        vstore, db_release, data.content
    )

    targeted_context, targeted_chunks = await get_branch_targeted_context(
        vstore,
        db_release,
        data.content,
        doc_branches,
        extra_text=chat_context,
    )

    print(
        f'[chat] chunks recuperados msg={len(msg_chunks)} '
        f'branch={len(branch_chunks)} direcionada={len(targeted_chunks)}'
    )

    all_chunks = _dedupe_chunks(
        branch_chunks + msg_chunks + targeted_chunks
    )
    context = '\n---\n'.join(
        msg_context
        + branch_context
        + targeted_context
        + auto_prompts
        + explicit_prompts
    )

    prompt = PROMPTS.CHAT.format(
        context=context,
        content=data.content,
        recent_messages=chat_context,
    )

    structured_model = model.with_structured_output(AnswerWithCitations)
    response: AnswerWithCitations = await structured_model.ainvoke(prompt)

    resolved_citations = resolve_citations(response.citations, all_chunks)

    if not resolved_citations and all_chunks:
        resolved_citations = _fallback_references(all_chunks)

    return {
        'answer': response.answer,
        'references': resolved_citations,
    }
