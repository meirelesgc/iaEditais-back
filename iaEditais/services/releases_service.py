import os
import shutil
import uuid
from http import HTTPStatus
from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile
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


def safe_file(file: UploadFile, upload_directory) -> str:
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

    latest_history = db_doc.history[0]
    file_path = safe_file(file, UPLOAD_DIRECTORY)
    db_release = await releases_repository.insert_db_release(
        latest_history, file_path, session, current_user
    )
    return db_release


async def process_release(
    model: Model,
    session: Session,
    vectorstore: VStore,
    db_release: DocumentRelease,
):
    check_tree = await releases_repository.get_check_tree(session, db_release)
    if not check_tree:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='There are no associated typifications',
        )
    chain = get_chain(model)
    input_vars = await get_vars(check_tree, session, vectorstore, db_release)
    response = await aplly_check_tree(chain, db_release, input_vars)
    return await save_result(session, db_release, check_tree, response)


def get_chain(model: Model):
    TEMPLATE = """
        <Edital>
        {docs}
        </Edital>

        Você é um analista especializado em avaliação de editais do serviço público brasileiro. Sua tarefa é verificar a presença e relevância dos seguintes critérios no edital fornecido:

        **Critério Principal:**
        Título: {taxonomy_title}
        Descrição: {taxonomy_description}
        Fonte: {taxonomy_source}

        **Critério Específico:**
        Título: {taxonomy_branch_title}
        Descrição: {taxonomy_branch_description}

        Com base no conteúdo do edital acima, responda às seguintes perguntas:

        1. O critério específico está contemplado no edital? Se sim, em qual seção ou parte?
        2. Qual é a relevância desse critério no contexto geral do edital?
        3. Há recomendações para aprimorar a inclusão ou a descrição desse critério no edital?

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
                    typification, taxonomy, branch, vectorstore
                )
                input_vars.append(_branch)
    return input_vars


async def process_branch(
    typification: Typification,
    taxonomy: Taxonomy,
    branch: Branch,
    vectorstore: VStore,
):
    sources = [f'{s.name}\n{s.description}' for s in typification.sources]
    query = f'{branch.title} {branch.description}'
    c = list()
    for d in await vectorstore.asimilarity_search(query, k=3):
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


async def aplly_check_tree(chain, release, input_vars):
    response = chain.batch(input_vars)
    return response


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


async def save_result(
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
