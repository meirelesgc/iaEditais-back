from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from iaEditais.core.settings import Settings

settings = Settings()

model = ChatOpenAI(
    model=settings.LLM_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=0.1,
)

fast_model = ChatOpenAI(
    model=settings.LLM_FAST_MODEL,
    api_key=settings.OPENAI_API_KEY,
    temperature=0,
)


async def get_model():  # pragma: no cover
    return model


def get_fast_model(model_name: Optional[str] = None) -> BaseChatModel:
    if not model_name:
        return fast_model
    return ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
