from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)


def get_model_001():
    model = 'gemini-2.0-flash-001'
    return ChatGoogleGenerativeAI(model=model), model


def get_model_002():
    model = 'gemini-2.0-flash'
    return ChatGoogleGenerativeAI(model=model), model


def get_model_003():
    model = 'gemini-2.5-pro-exp-03-25'
    return ChatGoogleGenerativeAI(model=model), model


def get_embed_001():
    model = 'models/text-embedding-004'
    return GoogleGenerativeAIEmbeddings(model=model), model


def get_embed_003():
    model = 'models/text-embedding-large-exp-03-07'
    return GoogleGenerativeAIEmbeddings(model=model), model


def main():
    models = [get_model_001, get_model_002, get_model_003]
    embed_models = [get_embed_001]
    return models, embed_models
