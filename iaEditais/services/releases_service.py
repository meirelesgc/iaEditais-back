import os
import shutil
import uuid
from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import Depends, File, HTTPException, UploadFile
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.vectorstores import VectorStore
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.database import get_session
from iaEditais.core.llm import get_model
from iaEditais.core.vectorstore import get_vectorstore
from iaEditais.models import (
    Branch,
    DocumentRelease,
    Taxonomy,
    Typification,
    User,
)
from iaEditais.repository import releases_repository
from iaEditais.schemas import DocumentReleaseFeedback
from iaEditais.security import get_current_user

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

    return file_path


async def create_release(
    doc_id: UUID,
    model: Model,
    session: Session,
    vectorstore: VStore,
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
    # await process_release(model, session, vectorstore, db_release)
    return db_release


async def process_release(
    model: Model,
    session: Session,
    vectorstore: VStore,
    release: DocumentRelease,
):
    check_tree = await releases_repository.get_check_tree(session, release)
    if not check_tree:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='There are no associated typifications',
        )
    chain = get_chain(model)
    input_vars = await get_vars(check_tree, session, vectorstore, release)

    print('Caminho feliz')


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
    for typification in check_tree:
        for taxonomy in typification.taxonomies:
            for branch in taxonomy.branches:
                _branch = await process_branch(
                    typification, taxonomy, branch, vectorstore
                )


async def process_branch(
    typification: Typification,
    taxonomy: Taxonomy,
    branch: Branch,
    vectorstore: VStore,
):
    sources = [f'{s.name}\n{s.description}' for s in {typification.sources}]
    query = f'{branch.title} {branch.description}'
    c = [d.page_content for d in vectorstore.similarity_search(query, k=3)]
    return {
        'docs': c,
        'taxonomy_title': taxonomy.title,
        'taxonomy_description': taxonomy.description,
        'taxonomy_source': sources,
        'taxonomy_branch_title': branch.title,
        'taxonomy_branch_description': branch.description,
        'query': 'Justifique sua resposta com base no conteúdo do edital.',
    }
