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


def parse_with_session(chunks):
    final_chunks = []
    for chunk in chunks:
        text = chunk.page_content.strip()

        session_match = re.search(r'^\s*(\d+\.\s+[A-ZÀ-Ú][A-ZÀ-Ú\s\.]*)', text)
        session_name = (
            session_match.group(1).strip()
            if session_match
            else 'SESSÃO NÃO ENCONTRADA'
        )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=0,
            separators=['\n', ' '],
        )
        subchunks = splitter.split_text(text)

        for subchunk in subchunks:
            formatted_text = (
                f'---\nSESSÃO: {session_name}\n---\n{subchunk.strip()}\n'
            )

            new_chunk = chunk.copy()
            new_chunk.page_content = formatted_text
            new_chunk.metadata = {**chunk.metadata, 'session': session_name}
            final_chunks.append(new_chunk)
    return final_chunks


def split_documents(documents):
    separators = [r'(?:(?<=^)|(?<=\n))\s*(?=\d+\.\s+[A-ZÀ-Ú])']
    session_splitter = RecursiveCharacterTextSplitter(
        chunk_overlap=0,
        is_separator_regex=True,
        keep_separator='start',
        separators=separators,
    )
    raw_chunks = session_splitter.split_documents(documents)
    chunks = parse_with_session(raw_chunks)

    return chunks
