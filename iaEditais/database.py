from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

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


engine = create_async_engine(Settings().DATABASE_URL)


async def get_session():  # pragma: no cover
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


async def get_vectorstore():  # pragma: no cover
    yield vectorstore
