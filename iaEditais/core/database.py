from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from iaEditais.core.settings import Settings

engine = create_async_engine(Settings().DATABASE_URL)


async def get_session():  # pragma: no cover
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
