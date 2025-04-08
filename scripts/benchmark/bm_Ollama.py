from langchain_ollama import ChatOllama, OllamaEmbeddings


def get_model_001():
    model = 'llama3.1:8b'
    return ChatOllama(model=model), model


def get_model_002():
    model = 'llama3.2:1b'
    return ChatOllama(model=model), model


def get_model_003():
    model = 'gemma2:9b'
    return ChatOllama(model=model), model


def get_model_004():
    model = 'gemma2:2b'
    return ChatOllama(model=model), model


def get_model_005():
    model = 'deepseek-r1:7b'
    return ChatOllama(model=model), model


def get_model_006():
    model = 'gemma3:4b'
    return ChatOllama(model=model), model


def get_model_007():
    model = 'deepseek-r1:1.5b'
    return ChatOllama(model=model), model


def get_model_008():
    model = 'gemma3:1b'
    return ChatOllama(model=model), model


def get_model_009():
    model = 'qwen2.5-coder:1.5b-base'
    return ChatOllama(model=model), model


def get_model_010():
    model = 'starcoder2:3b'
    return ChatOllama(model=model), model


def get_model_011():
    model = 'deepseek-coder:1.3b'
    return ChatOllama(model=model), model


def get_embed_001():
    model = 'nomic-embed-text:latest'
    return OllamaEmbeddings(model=model), model


def get_embed_002():
    model = 'mxbai-embed-large'
    return OllamaEmbeddings(model=model), model


def get_embed_003():
    model = 'all-minilm'
    return OllamaEmbeddings(model=model), model


def main():
    models = [
        get_model_001,
        get_model_002,
        get_model_003,
        get_model_004,
        get_model_005,
        get_model_006,
        get_model_007,
        get_model_008,
        get_model_009,
        get_model_010,
        get_model_011,
    ]
    embed_models = [get_embed_001, get_embed_002, get_embed_003]
    return models, embed_models
