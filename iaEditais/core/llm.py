from langchain_openai import ChatOpenAI

from iaEditais.core.settings import Settings

settings = Settings()
model = ChatOpenAI(
    model='gpt-5-mini',
    api_key=settings.OPENAI_API_KEY,
    temperature=0.1,
)


async def get_model():  # pragma: no cover
    return model
