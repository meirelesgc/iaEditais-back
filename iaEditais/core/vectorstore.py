from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from iaEditais.settings import Settings

vectorstore = PGVector(
    embeddings=OpenAIEmbeddings(
        model='text-embedding-3-small',
        api_key=Settings().OPENAI_API_KEY,
    ),
    connection=Settings().DATABASE_URL,
    use_jsonb=True,
    async_mode=True,
)


async def get_vectorstore():  # pragma: no cover
    yield vectorstore
