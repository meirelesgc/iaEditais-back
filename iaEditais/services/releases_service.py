import json
import os
import re
import shutil
import uuid
from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

import json5
from fastapi import Depends, File, HTTPException, UploadFile
from langchain.schema.runnable import RunnableLambda
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.vectorstores import VectorStore
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.database import get_session
from iaEditais.core.llm import get_model
from iaEditais.core.security import get_current_user
from iaEditais.core.vectorstore import get_vectorstore
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
    User,
)
from iaEditais.repositories import releases_repository
from iaEditais.schemas import DocumentReleaseFeedback

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
VStore = Annotated[VectorStore, Depends(get_vectorstore)]
Model = Annotated[BaseChatModel, Depends(get_model)]

UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'


async def save_file(file: UploadFile, upload_directory) -> str:
    os.makedirs(upload_directory, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f'{uuid.uuid4()}{file_extension}'
    file_path = os.path.join(upload_directory, unique_filename)

    try:
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        file.file.close()

    return f'/uploads/{unique_filename}'


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
    file_path = await save_file(file, UPLOAD_DIRECTORY)
    db_release = await releases_repository.insert_db_release(
        latest_history, file_path, session, current_user
    )
    return db_release


async def get_check_tree(session: Session, db_release: DocumentRelease):
    return await releases_repository.get_check_tree(session, db_release)


async def create_description(
    release: DocumentRelease,
    applied_branch: list[AppliedBranch],
    model: Model,
    session: Session,
):
    hits = []
    errors = []

    for branch in applied_branch:
        if branch.fulfilled:
            hits.append(branch)
        if not branch.fulfilled:
            errors.append(branch)

    description = str()
    prompt = """
        Gostaria que você elaborasse um resumo geral e sucinto dos pontos
        avaliados, destacando os melhores e os piores. Sintetize tudo em três
        ou quatro frases.
        """
    for branch in errors:
        prompt += (
            f'- {branch.title}: {branch.description or "sem descrição"}\n'
        )

    _ = model.invoke(prompt)
    description += _.content
    description += '\n\n'

    if errors:
        prompt = (
            'Elabore um resumo dos pontos que apresentaram problemas. '
            'Liste de forma clara e objetiva os seguintes itens:\n\n'
        )
        for branch in errors:
            prompt += (
                f'- {branch.title}: {branch.description or "sem descrição"}\n'
            )
    else:
        melhores = sorted(hits, key=lambda b: b.score or 0, reverse=True)[:3]
        prompt = 'Tudo está conforme. Crie um resumo positivo destacando os seguintes pontos:\n\n'
        for branch in melhores:
            prompt += (
                f'- {branch.title}: {branch.description or "sem descrição"}\n'
            )
    _ = model.invoke(prompt)
    description += _.content
    return await releases_repository.save_description(
        session, release, description
    )


def get_chain(model: Model):
    TEMPLATE = """
        <Documento>
        {docs}
        </Documento>

        Você é um analista especializado em avaliação de documentos com base em regras especificas. Sua tarefa é verificar a presença e relevância dos seguintes critérios no documento fornecido:

        **Critério Principal:**
        Título: {taxonomy_title}
        Descrição: {taxonomy_description}
        Fonte: {taxonomy_source}

        **Critério Específico:**
        Título: {taxonomy_branch_title}
        Descrição: {taxonomy_branch_description}

        Com base no conteúdo acima, responda às seguintes perguntas:

        1. O critério específico foi contemplado? Se sim, em qual seção ou parte?
        2. Qual é a relevância desse critério no contexto geral?
        3. Há recomendações para aprimorar a inclusão ou a descrição desse critério?

        {format_instructions}

        {query}
        """

    parser = JsonOutputParser(pydantic_object=DocumentReleaseFeedback)
    prompt = PromptTemplate(
        template=TEMPLATE,
        input_variables=[
            'docs',
            'taxonomy_title',
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
    session: Session,
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


async def process_branch(
    release: DocumentRelease,
    typification: Typification,
    taxonomy: Taxonomy,
    branch: Branch,
    vectorstore: VStore,
):
    sources = [f'{s.name}\n{s.description}' for s in typification.sources]
    query = f'{branch.title} {branch.description}'
    c = []
    path = release.file_path.split('/')[-1]

    allowed_source = f'iaEditais/storage/uploads/{path}'

    results = await vectorstore.asimilarity_search(
        query, k=3, filter={'source': allowed_source}
    )
    for d in results:
        c.append(d.page_content)

    return {
        'docs': c,
        'taxonomy_title': taxonomy.title,
        'taxonomy_description': taxonomy.description,
        'taxonomy_source': sources,
        'taxonomy_branch_title': branch.title,
        'taxonomy_branch_description': branch.description,
        'query': 'Justifique sua resposta com base no conteúdo do edital.',
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
        'score': 0,
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


async def apply_check_tree(chain: Model, release: DocumentRelease, input_vars):
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
    applied_branch = AppliedBranch(
        title=branch.title,
        description=branch.description,
        applied_taxonomy_id=applied_tax.id,
        original_id=branch.id,
        feedback=resp.get('feedback'),
        fulfilled=resp.get('fulfilled'),
        score=resp.get('score'),
    )
    session.add(applied_branch)
    return applied_branch


async def save_evaluation(
    session: Session,
    db_release: DocumentRelease,
    check_tree: list[Typification],
    response: list,
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
                applied_branch = await apply_branch(
                    session, applied_tax, branch, resp or {}
                )
                input_vars.append(applied_branch)
                response_index += 1

    await session.commit()
    return input_vars
