from langchain_deepseek import ChatDeepSeek
from langchain_openai import OpenAIEmbeddings


def get_model_001():
    model = 'deepseek-chat'
    return ChatDeepSeek(model=model), model


def get_model_002():
    model = 'deepseek-reasoner'
    return ChatDeepSeek(model=model), model


def get_embed_001():
    model = 'text-embedding-3-small'
    return OpenAIEmbeddings(model=model), model


def main():
    models = [get_model_001, get_model_001]
    embed_models = [get_embed_001]
    return models, embed_models
