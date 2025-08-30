import json
import threading
import time
from typing import Any, Dict, List

from fastapi import HTTPException
from langchain.callbacks.base import AsyncCallbackHandler, BaseCallbackHandler
from langchain.schema.document import Document
from langchain.schema.runnable import RunnableLambda
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import UsageMetadata, add_usage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy.exc import IntegrityError
from typing_extensions import override

from iaEditais.config import Settings
from iaEditais.models.doc import ReleaseFeedback
from iaEditais.repositories import source_repository


def load_documents(path: str):
    if path.endswith('.pdf'):
        document_loader = PyMuPDFLoader(path)
    if path.endswith('.pdf'):
        document_loader = Docx2txtLoader(path)
    return document_loader.load()


async def add_to_vector_store(path, vectorstore):
    documents = load_documents(path)
    chunks = split_documents(documents)
    try:
        await vectorstore.aadd_documents(chunks)
    except IntegrityError:
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
    chain = prompt | model | parser
    return chain


async def evaluate_branch(
    conn, branch, item, typification, release_id, db, chain
):
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


import redis.asyncio as aioredis


class StepProgressCallbackHandler(AsyncCallbackHandler):
    def __init__(self, redis_url, key):
        self.redis_url = redis_url
        self.key = key
        self.step = 0

    async def _get_redis(self):
        return aioredis.from_url(self.redis_url, decode_responses=True)

    async def _increment_step(self):
        self.step += 1
        status = {'status': 'pending', 'step': self.step}
        redis = await self._get_redis()
        await redis.set(self.key, json.dumps(status))
        await redis.publish(self.key, json.dumps(status))
        await redis.close()

    async def on_llm_end(self, response: LLMResult, **kwargs: Any):
        await self._increment_step()

    async def on_chat_model_start(self, *args, **kwargs):
        pass


async def process_release_taxonomy(chain, release, input_vars, key, redis):
    time_callback = TimingCallbackHandler()
    usage_callback = UsageMetadataCallbackHandler()
    step_callback = StepProgressCallbackHandler(Settings().REDIS_URL, key)
    safe_chain = safe_wrapper(chain)
    response = safe_chain.batch(
        input_vars,
        config={'callbacks': [usage_callback, time_callback, step_callback]},
    )

    for typification in release.taxonomy:
        for taxonomy in typification.get('taxonomy', []):
            for _, branch in enumerate(taxonomy.get('branch', [])):
                branch['evaluate'] = response[_]
                branch['usage'] = usage_callback.usage_metadata_list[_]
                branch['duration'] = time_callback.durations[_]
                branch['pages'] = input_vars[_]['pages']


async def process_branch(
    conn, typification, taxonomy, branch, vector_store: VectorStore
):
    source_ids = typification.get('source', []) + taxonomy.get('source', [])
    sources = []

    for source in await source_repository.source_get(conn):
        if source.get('id') in source_ids:
            sources.append(source.get('name'))

    docs = []
    pages = []
    query = f'{branch.get("title")} {branch.get("description")}'
    for d in await vector_store.asimilarity_search(query=query, k=3):
        docs.append(d.page_content)
        pages.append(d.metadata['page'])

    return {
        'pages': pages,
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
                input_vars.append(_branch)
    return input_vars


async def analyze_release(conn, vectorstore, model, key, release, redis):
    chain = build_prompt_chain(model)
    input_vars = await build_vars(conn, release, vectorstore)
    await process_release_taxonomy(chain, release, input_vars, key, redis)
    return release
