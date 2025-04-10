from langchain_deepseek import ChatDeepSeek


def get_model_001():
    model = 'deepseek-chat'
    return ChatDeepSeek(model=model), model


def get_model_002():
    model = 'deepseek-reasoner'
    return ChatDeepSeek(model=model), model


def main():
    models = [get_model_001, get_model_001]
    embed_models = []
    return models, embed_models
