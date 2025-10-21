from langchain_openai import ChatOpenAI

from iaEditais.core.settings import Settings

settings = Settings()
model = ChatOpenAI(
    model='gpt-4o-mini',
    api_key=settings.OPENAI_API_KEY,
)


async def get_model():
    return model
