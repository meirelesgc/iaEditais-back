from iaEditais.schemas.Order import ReleaseFeedback, Release
from iaEditais.repositories import SourceRepository
from typing import Any
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import PromptTemplate
from iaEditais.integrations import get_model, get_vector_store
from langchain.schema.document import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.exceptions import OutputParserException


def load_documents(path):
    document_loader = PyPDFLoader(path)
    return document_loader.load()


def add_to_vector_store(path):
    documents = load_documents(path)
    chunks = split_documents(documents)
    db = get_vector_store()
    db.add_documents(chunks)


def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=8000,
        chunk_overlap=800,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def calculate_chunk_ids(chunks):
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        source = chunk.metadata.get('source')
        page = chunk.metadata.get('page')
        current_page_id = f'{source}:{page}'

        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        chunk_id = f'{current_page_id}:{current_chunk_index}'
        last_page_id = current_page_id

        chunk.metadata['id'] = chunk_id

    return chunks


def build_prompt_chain() -> Any:
    TEMPLATE = """
        <Edital>
        {rag}
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

    parser = JsonOutputParser(pydantic_object=ReleaseFeedback)
    prompt = PromptTemplate(
        template=TEMPLATE,
        input_variables=[
            'rag',
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
    model = get_model()
    chain = prompt | model | parser
    return chain


def evaluate_branch(
    branch: dict,
    item: dict,
    typification: dict,
    release_id: str,
    db: Any,
    chain: Any,
) -> Any:
    source = []
    for s in SourceRepository.get_source():
        ss = item.get('source', []) + typification.get('source', [])
        if s['id'] in ss:
            source.append(s['name'])

    filter_source = {'source': {'$eq': f'storage/releases/{release_id}.pdf'}}
    query = f'{branch.get("title")} {branch.get("description")}'
    rag = []
    for d in db.similarity_search(query, k=3, filter=filter_source):
        rag.append(d.page_content)

    input_variables = {
        'rag': rag,
        'taxonomy_title': item.get('title'),
        'taxonomy_description': item.get('description'),
        'taxonomy_source': source,
        'taxonomy_branch_title': branch.get('title'),
        'taxonomy_branch_description': branch.get('description'),
        'query': 'Justifique sua resposta com base no conteúdo do edital.',
    }
    try:
        feedback = chain.invoke(input_variables)
        print('Sucesso')
    except OutputParserException:
        print('Erro')
    finally:
        return feedback


def process_release_taxonomy(release: Release, db: Any, chain: Any) -> None:
    for typification in release.taxonomy:
        for item in typification.get('taxonomy', []):
            for _, branch in enumerate(item.get('branch', [])):
                print(f'Número da revisão: {_}')
                branch['evaluate'] = evaluate_branch(
                    branch, item, typification, release.id, db, chain
                )


def analyze_release(release: Release) -> Release:
    db = get_vector_store()
    chain = build_prompt_chain()
    process_release_taxonomy(release, db, chain)
    return release
