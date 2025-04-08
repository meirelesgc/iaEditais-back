from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)


def get_model_002():
    model = 'gemini-2.0-flash'
    return ChatGoogleGenerativeAI(model=model), model


def get_embed_001():
    model = 'models/text-embedding-004'
    return GoogleGenerativeAIEmbeddings(model=model), model


def get_embed_003():
    model = 'models/text-embedding-large-exp-03-07'
    return GoogleGenerativeAIEmbeddings(model=model), model


def main():
    models = [get_model_002]
    embed_models = [get_embed_001]
    return models, embed_models
