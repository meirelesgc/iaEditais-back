import os
from itertools import product
from uuid import UUID, uuid4

from langchain.schema.document import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.vectorstores import InMemoryVectorStore, VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from iaEditais.repositories import source_repository, taxonomy_repository
from iaEditais.schemas import doc
from scripts.benchmark.bm_Ollama import main as benchmark_Ollama


class Benchmark(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model: str
    embedding_model: str
    verification_tree: list = []


def load_documents(path):
    document_loader = PyPDFLoader(path)
    return document_loader.load()


def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=8000,
        chunk_overlap=800,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)


def add_to_vector_store(path, vector_store):
    documents = load_documents(path)
    chunks = split_documents(documents)
    vector_store.add_documents(chunks)


def build_verification_tree(doc_id: UUID = None):
    tree = taxonomy_repository.get_typification(doc_id=doc_id)
    for typification in tree:
        ty_id = typification.get('id')
        typification['taxonomy'] = taxonomy_repository.get_taxonomy(ty_id)
        for taxonomy in typification['taxonomy']:
            tx_id = taxonomy.get('id')
            taxonomy['branch'] = taxonomy_repository.get_branches(tx_id)
    return tree


def build_prompt_chain(model):
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

    parser = JsonOutputParser(pydantic_object=doc.ReleaseFeedback)
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
    chain = prompt | model | parser
    return chain


def process_branch(typification, taxonomy, branch, chain, vector_store):
    source_ids = typification.get('source', []) + taxonomy.get('source', [])
    sources = []

    for source in source_repository.get_source():
        if source.get('id') in source_ids:
            sources.append(source.get('name'))

    docs = []
    query = f'{branch.get("title")} {branch.get("description")}'
    for d in vector_store.similarity_search(query, k=3):
        docs.append(d.page_content)

    input_vars = {
        'docs': docs,
        'taxonomy_title': taxonomy.get('title'),
        'taxonomy_description': taxonomy.get('description'),
        'taxonomy_source': sources,
        'taxonomy_branch_title': branch.get('title'),
        'taxonomy_branch_description': branch.get('description'),
        'query': 'Justifique sua resposta com base no conteúdo do edital.',
    }
    feedback = chain.invoke(input_vars)
    return feedback


def process_release(
    chain: RunnableSequence,
    vector_store: VectorStore,
    benchmark: Benchmark,
):
    for typification in benchmark.verification_tree:
        for taxonomy in typification.get('taxonomy', []):
            for branch in taxonomy.get('branch', []):
                branch['feedback'] = process_branch(
                    typification, taxonomy, branch, chain, vector_store
                )


if __name__ == '__main__':
    models = []
    embedding_models = []

    providers = [benchmark_Ollama]

    for provider in providers:
        _models, _embedding_models = provider()
        models += _models
        embedding_models += _embedding_models

    PATH = 'storage/benchmark'
    for file in os.listdir(PATH):
        for _model, _embedding_model in product(models, embedding_models):
            model = _model()
            vector_store = InMemoryVectorStore(_embedding_model())

            benchmark = Benchmark(
                model=_model().model,
                embedding_model=_embedding_model().model,
                verification_tree=build_verification_tree(),
            )

            add_to_vector_store(f'{PATH}/{file}', vector_store)
            chain = build_prompt_chain(model)
            process_release(chain, vector_store, benchmark)
            break
        break
