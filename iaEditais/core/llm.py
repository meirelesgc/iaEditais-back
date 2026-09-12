from langchain_openai import ChatOpenAI

from iaEditais.core.settings import Settings

settings = Settings()
model = ChatOpenAI(
    model=settings.LLM_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=settings.LLM_TEMPERATURE,
)


async def get_model():  # pragma: no cover
    return model
