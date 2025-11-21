from functools import cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector

from iaEditais.config import Settings


@cache
def get_model():
    return ChatOpenAI(
        model='gpt-4o-mini-2024-07-18',
        temperature=0,
        api_key=Settings().OPENAI_API_KEY,
    )


@cache
def get_embedding_function():
    return OpenAIEmbeddings(
        model='text-embedding-3-large',
        api_key=Settings().OPENAI_API_KEY,
    )


@cache
def get_vector_store():
    return PGVector(
        embeddings=get_embedding_function(),
        collection_name='fiotec',
        connection=Settings().get_connection_string_psycopg3(),
        use_jsonb=True,
    )
