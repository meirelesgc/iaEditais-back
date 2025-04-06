from langchain_ollama import OllamaEmbeddings, OllamaLLM


def get_model_001():
    return OllamaLLM(model='llama3.1:8b')


def get_model_002():
    return OllamaLLM(model='llama3.2:1b')


def get_embed_001():
    return OllamaEmbeddings(model='nomic-embed-text:latest')


def main():
    models = [get_model_001, get_model_002]
    embed_models = [get_embed_001]
    return models, embed_models
