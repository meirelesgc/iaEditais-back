from langchain_ollama import ChatOllama, OllamaEmbeddings


def get_model_001():
    model = 'llama3.1:8b'
    return ChatOllama(model=model, base_url='http://localhost:11434'), model


def get_model_004():
    model = 'gemma2:2b'
    return ChatOllama(model=model, base_url='http://localhost:11434'), model


def get_model_005():
    model = 'deepseek-r1:7b'
    return ChatOllama(model=model, base_url='http://localhost:11434'), model


def get_model_006():
    model = 'gemma3:4b'
    return ChatOllama(model=model, base_url='http://localhost:11434'), model


def get_model_007():
    model = 'deepseek-r1:1.5b'
    return ChatOllama(model=model, base_url='http://localhost:11434'), model


def get_embed_001():
    model = 'nomic-embed-text:latest'
    return OllamaEmbeddings(
        model=model, base_url='http://localhost:11434'
    ), model


def get_embed_002():
    model = 'mxbai-embed-large:latest'
    return OllamaEmbeddings(
        model=model, base_url='http://localhost:11434'
    ), model


def main():
    models = [
        get_model_006,
        get_model_001,
        get_model_004,
        get_model_005,
        get_model_007,
    ]
    embed_models = [get_embed_001, get_embed_002]

    return models, embed_models
