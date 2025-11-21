# from langchain_ollama import ChatOllama
from arrange.config import Settings
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model='gpt-4o-mini', api_key=Settings().OPENAI_API_KEY)
# model = ChatOllama(model='gemma3:4b')


async def get_local_model():
    return model
