from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from iaEditais.config import Settings
from functools import cache


@cache
def get_model():
    return ChatOpenAI(
        model='gpt-4o',
        temperature=0,
        api_key=Settings().OPENAI_API_KEY,
    )


@cache
def get_embedding_function(text):
    return OpenAIEmbeddings(
        model='text-embedding-3-small',
        api_key=Settings().OPENAI_API_KEY,
    )
