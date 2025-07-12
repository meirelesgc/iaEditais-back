import threading
import time
from typing import Any, Dict, List

from fastapi import HTTPException
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema.document import Document
from langchain.schema.runnable import RunnableLambda
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import UsageMetadata, add_usage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.exc import IntegrityError
from typing_extensions import override

from iaEditais.integrations.database import get_model, get_vector_store
from iaEditais.models.doc import Release, ReleaseFeedback
from iaEditais.repositories import source_repository


def load_documents(path):
    document_loader = PyMuPDFLoader(path)
    return document_loader.load()


def add_to_vector_store(path):
    documents = load_documents(path)
    chunks = split_documents(documents)
    db = get_vector_store()
    try:
        db.add_documents(chunks)
    except IntegrityError as E:
        print('IntegrityErro    r', '\n\n', E)
        raise HTTPException(
            status_code=415,
            detail='At least one typification must be selected.',
        )


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
        """  # noqa: E501

    parser = JsonOutputParser(pydantic_object=ReleaseFeedback)
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
    model = get_model()
    chain = prompt | model | parser
    return chain


async def evaluate_branch(  # noqa: PLR0913, PLR0917
    conn,
    branch: dict,
    item: dict,
    typification: dict,
    release_id: str,
    db: Any,
    chain: Any,
) -> Any:
    source = []
    for s in await source_repository.source_get(conn):
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
    except OutputParserException:
        feedback = {
            'feedback': 'Não foi possível gerar feedback para este item.',
            'fulfilled': False,
        }
    finally:
        return feedback


class TimingCallbackHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.start_times: Dict[str, float] = {}
        self.durations: list[float] = []

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        run_id = kwargs.get('run_id', str(time.time_ns()))
        with self._lock:
            self.start_times[run_id] = time.perf_counter()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        run_id = kwargs.get('run_id', str(time.time_ns()))
        end_time = time.perf_counter()
        with self._lock:
            start_time = self.start_times.pop(run_id, None)
            if start_time is not None:
                duration = end_time - start_time
                quota = 14 - duration
                if quota > 0:
                    # sleep(quota)
                    pass
                self.durations.append(duration)

    def get_average_duration(self) -> float:
        with self._lock:
            if not self.durations:
                return 0.0
            return sum(self.durations) / len(self.durations)

    def __repr__(self) -> str:
        return f'Avg duration: {self.get_average_duration():.4f}s, Count: {len(self.durations)}'  # noqa: E501


class UsageMetadataCallbackHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.usage_metadata: dict[str, UsageMetadata] = {}
        self.usage_metadata_list: list[UsageMetadata] = []

    @override
    def __repr__(self) -> str:
        return str(self.usage_metadata)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        try:
            generation = response.generations[0][0]
        except IndexError:
            generation = None

        usage_metadata = None
        if isinstance(generation, ChatGeneration):
            try:
                message = generation.message
                if isinstance(message, AIMessage):
                    usage_metadata = message.usage_metadata
            except AttributeError:
                pass

        if usage_metadata:
            with self._lock:
                self.usage_metadata = add_usage(
                    self.usage_metadata, usage_metadata
                )
                self.usage_metadata_list.append(usage_metadata)


def safe_wrapper(chain: Runnable):
    def _safe_invoke(input_item):
        try:
            return chain.invoke(input_item)
        except OutputParserException:
            return {
                'feedback': 'Não foi possível gerar feedback para este item.',
                'fulfilled': False,
            }

    return RunnableLambda(_safe_invoke)


async def process_release_taxonomy(chain, release, input_vars):
    time_callback = TimingCallbackHandler()
    usage_callback = UsageMetadataCallbackHandler()
    safe_chain = safe_wrapper(chain)
    response = safe_chain.batch(
        input_vars, config={'callbacks': [usage_callback, time_callback]}
    )
    for typification in release.taxonomy:
        for taxonomy in typification.get('taxonomy', []):
            for _, branch in enumerate(taxonomy.get('branch', [])):
                branch['evaluate'] = response[_]
                branch['usage'] = usage_callback.usage_metadata_list[_]
                branch['duration'] = time_callback.durations[_]


async def process_branch(conn, typification, taxonomy, branch, vector_store):
    source_ids = typification.get('source', []) + taxonomy.get('source', [])
    sources = []

    for source in await source_repository.source_get(conn):
        if source.get('id') in source_ids:
            sources.append(source.get('name'))

    docs = []
    query = f'{branch.get("title")} {branch.get("description")}'
    for d in vector_store.similarity_search(query, k=3):
        docs.append(d.page_content)

    return {
        'docs': docs,
        'taxonomy_title': taxonomy.get('title'),
        'taxonomy_description': taxonomy.get('description'),
        'taxonomy_source': sources,
        'taxonomy_branch_title': branch.get('title'),
        'taxonomy_branch_description': branch.get('description'),
        'query': 'Justifique sua resposta com base no conteúdo do edital.',
    }


async def build_vars(conn, release, vectorstore):
    input_vars = list()
    for typification in release.taxonomy:
        for taxonomy in typification.get('taxonomy', []):
            for branch in taxonomy.get('branch', []):
                _branch = await process_branch(conn, typification, taxonomy, branch, vectorstore)  # fmt: skip # noqa: E261, E501
                input_vars.append(_branch)  # fmt: skip # noqa: E261, E501
    return input_vars


async def analyze_release(conn, release: Release) -> Release:
    db = get_vector_store()
    chain = build_prompt_chain()
    input_vars = await build_vars(conn, release, db)
    await process_release_taxonomy(chain, release, input_vars)
    return release
