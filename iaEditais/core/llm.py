from langchain_openai import ChatOpenAI

from iaEditais.core.settings import Settings

settings = Settings()
model = ChatOpenAI(
    model='gpt-5-nano-2025-08-07',
    api_key=settings.OPENAI_API_KEY,
    temperature=0.1,
)


async def get_model():
    return model
