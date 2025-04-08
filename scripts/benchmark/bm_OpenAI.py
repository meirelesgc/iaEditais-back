from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def get_model_001():
    model = 'gpt-4.5-preview'
    return ChatOpenAI(model=model), model


def get_model_002():
    model = 'gpt-4o'
    return ChatOpenAI(model=model), model


def get_model_003():
    model = 'gpt-4o-mini'
    return ChatOpenAI(model=model), model


def get_model_004():
    model = 'o3-mini'
    return ChatOpenAI(model=model), model


def get_embed_001():
    model = 'text-embedding-3-small'
    return OpenAIEmbeddings(model=model), model


def get_embed_002():
    model = 'text-embedding-3-large'
    return OpenAIEmbeddings(model=model), model


def get_embed_003():
    model = 'text-embedding-ada-002'
    return OpenAIEmbeddings(model=model), model


def get_model_005():
    model = 'o1-mini'
    return ChatOpenAI(model=model), model


def main():
    models = [get_model_002, get_model_003, get_model_004, get_model_005]
    embed_models = [get_embed_001, get_embed_002, get_embed_003]
    return models, embed_models
