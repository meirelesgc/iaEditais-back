from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from iaEditais.core.settings import Settings

settings = Settings()
vectorstore = PGVector(
    embeddings=OpenAIEmbeddings(
        model='text-embedding-3-small',
        api_key=settings.OPENAI_API_KEY,
    ),
    connection=settings.DATABASE_URL,
    use_jsonb=True,
    async_mode=True,
)


async def get_vectorstore():  # pragma: no cover
    yield vectorstore
