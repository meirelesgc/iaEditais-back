import csv
import os
import threading
import time
from itertools import product
from typing import Any, Dict, List
from uuid import UUID, uuid4

import pandas as pd
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema.document import Document
from langchain.schema.runnable import RunnableLambda
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import UsageMetadata, add_usage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import InMemoryVectorStore, VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from typing_extensions import override

from iaEditais.config import Settings
from iaEditais.repositories import source_repository, taxonomy_repository
from iaEditais.schemas import doc
from scripts.benchmark.bm_DeepSeek import main as benchmark_Deepseek
from scripts.benchmark.bm_Google import main as benchmark_Google
from scripts.benchmark.bm_Ollama import main as benchmark_Ollama
from scripts.benchmark.bm_OpenAI import main as benchmark_OpenAi


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


class Benchmark(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model: str
    embedding_model: str
    verification_tree: list = []
    usage: dict = {}
    duration: float = None


class TimingCallbackHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        super().__init__()
        self._lock = threading.Lock()
        self.start_times: Dict[str, float] = {}
        self.durations: list[float] = []

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        print('[START]', end=' ')
        run_id = kwargs.get('run_id', str(time.time_ns()))
        with self._lock:
            self.start_times[run_id] = time.perf_counter()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        print('[END]', end=' ')
        run_id = kwargs.get('run_id', str(time.time_ns()))
        end_time = time.perf_counter()
        with self._lock:
            start_time = self.start_times.pop(run_id, None)
            if start_time is not None:
                duration = end_time - start_time
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


def load_documents(path):
    document_loader = PyPDFLoader(path)
    return document_loader.load()


def split_documents(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
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


def process_branch(typification, taxonomy, branch, vector_store):
    source_ids = typification.get('source', []) + taxonomy.get('source', [])
    sources = []

    for source in source_repository.get_source():
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


def build_vars(
    vector_store: VectorStore,
    benchmark: Benchmark,
):
    input_vars = []
    for typification in benchmark.verification_tree:
        for taxonomy in typification.get('taxonomy', []):
            for branch in taxonomy.get('branch', []):
                input_vars.append(process_branch(typification, taxonomy, branch, vector_store))  # fmt: skip  # noqa: E261, E501
    return input_vars


def process_release(
    chain: Runnable,
    benchmark: Benchmark,
    input_vars: list,
):
    time_callback = TimingCallbackHandler()
    callback = UsageMetadataCallbackHandler()
    safe_chain = safe_wrapper(chain)
    response = safe_chain.batch(
        input_vars, config={'callbacks': [callback, time_callback]}
    )
    benchmark.usage = callback.usage_metadata
    benchmark.duration = sum(time_callback.durations)

    for typification in benchmark.verification_tree:
        for taxonomy in typification.get('taxonomy', []):
            for _, branch in enumerate(taxonomy.get('branch', [])):
                branch['feedback'] = response[_]
                branch['usage'] = callback.usage_metadata_list[_]
                branch['duration'] = time_callback.durations[_]


def format_benchmarks(benchmarks):
    formatd_benchmarks = []
    for benchmark in benchmarks:
        for typification in benchmark['verification_tree']:
            for taxonomy in typification['taxonomy']:
                for branche in taxonomy['branch']:
                    formated_branch = {
                        'id': benchmark.get('id'),
                        'model': benchmark.get('model'),
                        'embedding_model': benchmark.get('embedding_model'),
                        'total_input_tokens': benchmark.get('usage').get(
                            'input_tokens'
                        ),
                        'total_output_tokens': benchmark.get('usage').get(
                            'output_tokens'
                        ),
                        'total_total_tokens': benchmark.get('usage').get(
                            'total_tokens'
                        ),
                        'total_duration': benchmark.get('duration'),
                        'typification': taxonomy.get('name'),
                        'taxonomy': taxonomy.get('title'),
                        'taxonomy_description': taxonomy.get('description'),
                        'branch': branche.get('title'),
                        'branch_description': branche.get('description'),
                        'feedback': branche.get('feedback').get('fulfilled'),
                        'feedback_description': branche.get('feedback').get(
                            'feedback'
                        ),
                        'input_tokens': branche.get('usage').get('input_tokens'),
                        'output_tokens': branche.get('usage').get(
                            'output_tokens'
                        ),
                        'total_tokens': branche.get('usage').get('total_tokens'),
                        'duration': branche.get('duration'),
                    }
                    formatd_benchmarks.append(formated_branch)
    return formatd_benchmarks


if __name__ == '__main__':
    os.environ['OPENAI_API_KEY'] = Settings().OPENAI_API_KEY
    os.environ['GOOGLE_API_KEY'] = Settings().GOOGLE_API_KEY
    os.environ['DEEPSEEK_API_KEY'] = Settings().DEEPSEEK_API_KEY

    benchmarks = []
    models = []
    embedding_models = []

    providers = [
        benchmark_Google,
        benchmark_OpenAi,
        benchmark_Deepseek,
        benchmark_Ollama,
    ]

    for provider in providers:
        _models, _embedding_models = provider()
        models += _models
        embedding_models += _embedding_models

    PATH = 'storage/benchmark'
    for file in os.listdir(PATH):
        print('Analisando o arquivo: ', file)
        print('Utilizando modelos:')
        for _model, _embedding_model in product(models, embedding_models):
            _model_object, _model_name = _model()
            _embedding_object, _embedding_name = _embedding_model()
            print(f'[{_model_name} x {_embedding_name}]')

            vector_store = InMemoryVectorStore(_embedding_object)

            benchmark = Benchmark(
                model=_model_name,
                embedding_model=_embedding_name,
                verification_tree=build_verification_tree(),
            )

            print('Adicionando a VectorStore | Start')
            add_to_vector_store(f'{PATH}/{file}', vector_store)
            print('Adicionando a VectorStore | End')
            chain = build_prompt_chain(_model_object)
            input_vars = build_vars(vector_store, benchmark)
            print('Processando a carga | Start')
            process_release(chain, benchmark, input_vars)
            print('Processando a carga | End')
            benchmarks.append(benchmark.model_dump())
    benchmarks = format_benchmarks(benchmarks)
    PATH = 'storage/benchmark/benchmark.csv'
    pd.DataFrame(benchmarks).to_csv(PATH, index=False, quoting=csv.QUOTE_ALL)
