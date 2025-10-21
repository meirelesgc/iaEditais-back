import os

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)


async def load_document(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        loader = PyMuPDFLoader(file_path)
    elif ext == '.docx':
        loader = Docx2txtLoader(file_path)
    elif ext == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')
    print('Loader de documentos')
    return loader.load()
