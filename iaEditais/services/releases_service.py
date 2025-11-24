import json
import os
import re
from http import HTTPStatus
from typing import List, Optional
from uuid import UUID

import json5
from fastapi import File, HTTPException, UploadFile
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableLambda

from iaEditais import prompts as PROMPTS
from iaEditais.core.dependencies import CurrentUser, Model, Session, VStore
from iaEditais.models import (
    AppliedBranch,
    AppliedSource,
    AppliedTaxonomy,
    AppliedTypification,
    AppliedTypificationSource,
    Branch,
    DocumentRelease,
    Source,
    Taxonomy,
    Typification,
)
from iaEditais.repositories import releases_repository
from iaEditais.schemas import DocumentReleaseFeedback
from iaEditais.services import storage_service

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'
SIMILARITY_THRESHOLD = 0.5
MAX_CHUNKS = 5


async def create_release(
    doc_id: UUID,
    session: Session,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    allowed_content_types = {
        'text/plain',
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    }

    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail='Invalid file type. Only Word and PDF files are allowed.',
        )
    db_doc = await releases_repository.get_db_doc(doc_id, session)

    if not db_doc:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document not found',
        )

    if not db_doc.history:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Document does not have a history to attach the file.',
        )

    if len(db_doc.typifications) == 0:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='There are no associated typifications',
        )
    latest_history = db_doc.history[0]
    file_path = await storage_service.save_file(file, UPLOAD_DIRECTORY)
    db_release = await releases_repository.insert_db_release(
        latest_history, file_path, session, current_user
    )
    return db_release


async def get_check_tree(session: Session, db_release: DocumentRelease):
    return await releases_repository.get_check_tree(session, db_release)


async def create_description(
    release: DocumentRelease,
    applied_branches: List[AppliedBranch],
    model: Model,
    session: Session,
):
    hits = [b for b in applied_branches if b.fulfilled]
    errors = [b for b in applied_branches if not b.fulfilled]

    def _format_branch_line(branch: AppliedBranch) -> str:
        description = branch.description or 'sem descrição'
        evaluation = branch.evaluation
        feedback = evaluation.get('feedback') or 'Sem feedback'
        fulfilled = evaluation.get('fulfilled')
        score = evaluation.get('score')

        status = (
            'Contemplado'
            if fulfilled
            else 'Não contemplado'
            if fulfilled is not None
            else 'Problema na análise'
        )

        return f'- {branch.title}: {description} | {status} | Nota: {score or "N/A"} | Feedback: {feedback}\n'

    description_parts: List[str] = []

    hits_text = ''.join(_format_branch_line(b) for b in hits[:3])
    errors_text = ''.join(_format_branch_line(b) for b in errors[:3])
    summary_prompt = (
        PROMPTS.DESCRIPTION
        + '\n\nAplicadas (contempladas):\n'
        + (hits_text or 'Nenhuma ramificação bem-sucedida.\n')
        + '\nErros:\n'
        + (errors_text or 'Nenhuma ramificação com erro.\n')
    )

    summary_response = model.invoke(summary_prompt)
    description_parts.append(summary_response.content.strip())

    if errors:
        prompt = PROMPTS.ERROR_SUMMARY
        prompt += ''.join(_format_branch_line(b) for b in errors)
    else:
        top_hits = sorted(hits, key=lambda b: (b.score or 0), reverse=True)[:3]
        prompt = PROMPTS.SUCCESS_SUMMARY
        prompt += ''.join(_format_branch_line(b) for b in top_hits)

    response = model.invoke(prompt)

    description_parts.append(response.content.strip())

    final_description = '\n\n'.join(description_parts)
    return await releases_repository.save_description(
        session, release, final_description
    )


def get_chain(model: Model):
    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)
    prompt = PromptTemplate(
        template=PROMPTS.DOCUMENT_ANALYSIS_PROMPT,
        input_variables=[
            'docs',
            'taxonomy_title',
            'typification_source',
            'typification_source_content',
            'taxonomy_description',
            'taxonomy_source',
            'taxonomy_branch_title',
            'taxonomy_branch_description',
            'format_instructions',
            'query',
        ],
        partial_variables={
            'format_instructions': parser.get_format_instructions()
        },
    )

    return prompt | model | parser


async def get_vars(
    check_tree: list[Typification],
    vectorstore: VStore,
    release: DocumentRelease,
):
    input_vars = list()
    for typification in check_tree:
        for taxonomy in typification.taxonomies:
            for branch in taxonomy.branches:
                _branch = await process_branch(
                    release, typification, taxonomy, branch, vectorstore
                )
                input_vars.append(_branch)
    return input_vars


async def fetch_similar_contents_doc(
    vectorstore: VStore, release: DocumentRelease, query: str, session: str
):
    if not session:
        return []

    path = release.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'

    results = await vectorstore.asimilarity_search_with_score(
        query,
        k=MAX_CHUNKS,
        filter={'source': allowed_source, 'session': session},
    )

    # Agora retornamos o objeto Document inteiro + score
    filtered = [
        (d, score) for d, score in results if score < SIMILARITY_THRESHOLD
    ]

    return filtered


async def fetch_similar_contents_source(
    vectorstore: VStore, source: Source, query: str, session: str
):
    if not session:
        return []

    path = source.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'

    results = await vectorstore.asimilarity_search_with_score(
        query,
        k=MAX_CHUNKS,
        filter={'source': allowed_source, 'session': session},
    )

    filtered = [
        (d, score) for d, score in results if score < SIMILARITY_THRESHOLD
    ]

    return filtered


async def get_doc_session(
    vectorstore: VStore, release: DocumentRelease, query: str
):
    path = release.file_path.split('/')[-1]
    allowed_source = f'iaEditais/storage/uploads/{path}'
    results = await vectorstore.asimilarity_search(
        query, k=1, filter={'source': allowed_source}
    )
    if not results:
        return None
    return results[0].metadata.get('session')


async def process_branch(
    release: DocumentRelease,
    typification: Typification,
    taxonomy: Taxonomy,
    branch: Branch,
    vectorstore: VStore,
):
    query = f'{taxonomy.title}: {taxonomy.description or ""}'.strip()
    session = await get_doc_session(vectorstore, release, query)
    if not session:
        return {
            'presidio_mapping': {},
            'docs': 'Nenhum conteúdo relacionado encontrado para avaliação.',
            'taxonomy_title': taxonomy.title.strip(),
            'taxonomy_description': (taxonomy.description or '').strip(),
            'taxonomy_source': '',
            'taxonomy_branch_title': branch.title.strip(),
            'taxonomy_branch_description': (branch.description or '').strip(),
            'typification_source': '',
            'query': 'Justifique sua resposta com base no conteúdo do edital.',
            'prompt_score': 0,
        }

    query = f'{branch.title}: {branch.description or ""}'.strip()
    retrieved_contents = await fetch_similar_contents_doc(
        vectorstore, release, query, session
    )

    docs_text = 'Nenhum conteúdo encontrado.'
    prompt_score = 0
    presidio_mapping = {}

    if isinstance(retrieved_contents, list) and retrieved_contents:
        docs_text = '\n\n'.join([
            d.page_content.strip()
            for d, _ in retrieved_contents
            if d.page_content.strip()
        ])
        os.system('clear')
        presidio_mapping = {
            k: v
            for d, _ in retrieved_contents
            if d.metadata and 'presidio_mapping' in d.metadata
            for k, v in d.metadata['presidio_mapping'].items()
        }
        prompt_score += sum(score for _, score in retrieved_contents)

    typification_sources_text = []
    for source in getattr(typification, 'sources', []):
        chunks = []
        if getattr(source, 'file_path', None):
            chunks = await fetch_similar_contents_source(
                vectorstore, source, query, session
            )

        chunk_text = ''
        if isinstance(chunks, list) and chunks:
            chunk_text = ' '.join([
                d.page_content.strip()
                for d, _ in chunks
                if d.page_content.strip()
            ])

        source_block = (
            f'Nome da Fonte: {source.name}\n'
            f'Descrição: {source.description or "sem descrição"}\n'
            f'Conteúdo Relevante: {chunk_text or "nenhum conteúdo relevante encontrado"}'
        )
        typification_sources_text.append(source_block.strip())

    taxonomy_sources_text = []
    for source in getattr(taxonomy, 'sources', []):
        source_text = f'{source.name}\n{source.description or "sem descrição"}'
        taxonomy_sources_text.append(source_text.strip())

    typification_source_content = '\n\n---\n\n'.join(
        typification_sources_text
    ).strip()
    taxonomy_source_content = '\n\n'.join(taxonomy_sources_text).strip()

    return {
        'presidio_mapping': presidio_mapping,
        'docs': docs_text,
        'taxonomy_title': taxonomy.title.strip(),
        'taxonomy_description': (taxonomy.description or '').strip(),
        'taxonomy_source': taxonomy_source_content,
        'taxonomy_branch_title': branch.title.strip(),
        'taxonomy_branch_description': (branch.description or '').strip(),
        'typification_source': typification_source_content,
        'query': 'Justifique sua resposta com base no conteúdo do edital.',
        'prompt_score': prompt_score,
    }


def try_recover_json(msg: str):
    json_match = re.search(r'\{[\s\S]*\}', msg)
    if not json_match:
        return None

    raw_json = json_match.group(0)
    cleaned = (
        raw_json.replace('```json', '')
        .replace('```', '')
        .replace('\n', ' ')
        .replace('\r', ' ')
        .strip()
    )
    cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    try:
        return json.loads(cleaned)
    except Exception:
        try:
            return json5.loads(cleaned)
        except Exception:
            return None


def normalize_output(data):
    default = {
        'fulfilled': False,
        'score': -1,
        'feedback': 'Não foi possível gerar feedback para este item.',
    }

    if not isinstance(data, dict):
        return default

    fulfilled = bool(data.get('fulfilled', False))
    score = (
        int(data.get('score', 0))
        if isinstance(data.get('score', (int, float)), (int, float))
        else 0
    )
    feedback = str(data.get('feedback', default['feedback']))

    return {'fulfilled': fulfilled, 'score': score, 'feedback': feedback}


def safe_wrapper(chain):
    def _safe_invoke(input_item):
        try:
            result = chain.invoke(input_item)
            return normalize_output(result)
        except OutputParserException as e:
            msg = str(e)
            recovered = try_recover_json(msg)
            if recovered:
                return normalize_output(recovered)
            return normalize_output(None)

        except Exception:
            return normalize_output(None)

    return RunnableLambda(_safe_invoke)


async def apply_check_tree(chain: Model, input_vars):
    safe_chain = safe_wrapper(chain)
    result = await safe_chain.abatch(input_vars)
    return result


async def apply_typification(
    session: Session,
    db_release: DocumentRelease,
    typification: Typification,
):
    applied_typ = AppliedTypification(
        name=typification.name,
        applied_release_id=db_release.id,
        original_id=typification.id,
    )
    session.add(applied_typ)
    await session.flush()
    return applied_typ


async def apply_source(session: Session, source_cache: dict, source: Source):
    key = getattr(source, 'id', None) or getattr(source, 'name', None)
    applied_src = source_cache.get(key)
    if not applied_src:
        applied_src = AppliedSource(
            name=source.name,
            description=getattr(source, 'description', None),
            original_id=getattr(source, 'id', None),
        )
        session.add(applied_src)
        await session.flush()
        source_cache[key] = applied_src
    return applied_src


async def link_typification_sources(
    session: Session,
    applied_typ: AppliedTypification,
    typification: Typification,
    source_cache: dict,
):
    for source in getattr(typification, 'sources', []):
        applied_src = await apply_source(session, source_cache, source)
        session.add(
            AppliedTypificationSource(
                typification_id=applied_typ.id,
                source_id=applied_src.id,
            )
        )


async def apply_taxonomy(
    session: Session, applied_typ: AppliedTypification, taxonomy: Taxonomy
):
    applied_tax = AppliedTaxonomy(
        title=taxonomy.title,
        description=taxonomy.description,
        applied_typification_id=applied_typ.id,
        original_id=taxonomy.id,
    )
    session.add(applied_tax)
    await session.flush()
    return applied_tax


async def apply_branch(
    session: Session,
    applied_tax: AppliedTaxonomy,
    branch: 'Branch',
    resp: dict,
):
    CUTTING_LINE = 5
    applied_branch = AppliedBranch(
        title=branch.title,
        description=branch.description,
        applied_taxonomy_id=applied_tax.id,
        original_id=branch.id,
        feedback=resp.get('feedback'),
        fulfilled=True if resp.get('score', 0) > CUTTING_LINE else False,
        score=resp.get('score', 0),
        presidio_mapping=str(resp.get('presidio_mapping')),
    )
    session.add(applied_branch)
    return applied_branch


async def save_evaluation(
    session: Session,
    db_release: DocumentRelease,
    check_tree: list[Typification],
    response: list,
    real_input_vars: list,
):
    input_vars = []
    response_index = 0
    source_cache: dict[Optional[UUID], 'AppliedSource'] = {}

    for typification in check_tree:
        applied_typ = await apply_typification(
            session, db_release, typification
        )
        await link_typification_sources(
            session, applied_typ, typification, source_cache
        )

        for taxonomy in typification.taxonomies:
            applied_tax = await apply_taxonomy(session, applied_typ, taxonomy)

            for branch in taxonomy.branches:
                resp = (
                    response[response_index]
                    if response_index < len(response)
                    else {}
                )
                presidio_vars = (
                    real_input_vars[response_index]
                    if response_index < len(real_input_vars)
                    else {}
                )
                presidio_mapping = presidio_vars.get('presidio_mapping', {})

                resp = {**(resp or {}), 'presidio_mapping': presidio_mapping}

                applied_branch = await apply_branch(
                    session, applied_tax, branch, resp
                )

                input_vars.append(applied_branch)
                response_index += 1

    await session.commit()
    return input_vars
