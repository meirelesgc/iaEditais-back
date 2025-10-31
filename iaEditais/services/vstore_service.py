import os
import re

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter


async def load_document(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        loader = PyMuPDFLoader(file_path, mode='single')
    elif ext == '.docx':
        loader = Docx2txtLoader(file_path, mode='single')
    elif ext == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')
    docs = loader.load()
    for d in docs:
        d.page_content = clean_text(d.page_content)
    return docs


def clean_text(text):
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', text)
    text = text.replace('\x0c', '\n')
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+\n', '\n', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'[ ]{2,}', ' ', text)
    return text.strip()


def split_documents(documents):
    separators = [
        r'(?:^|\n)\s*(\d+)\.\s+(?!\d+\.)([^a-záéíóúâêôãõç\n\r]+)',
        r'\d+\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ\s]+(?=\n)',
    ]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=180,
        is_separator_regex=True,
        keep_separator='start',
        separators=separators,
    )
    chunks = text_splitter.split_documents(documents)
    return chunks
