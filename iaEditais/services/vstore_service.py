import os
import uuid
from pathlib import Path
from typing import List

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from iaEditais.core.dependencies import VStore
from iaEditais.core.settings import Settings
from iaEditais.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=750,
    chunk_overlap=50,
)


def _with_chunk_ids(chunks: List[Document], source_id: str) -> List[Document]:
    total = len(chunks)
    chunk_ids = [f'{source_id}:{i:06d}' for i in range(total)]

    for i, d in enumerate(chunks):
        md = dict(d.metadata or {})
        md['source_id'] = source_id
        md['chunk_index'] = i
        md['chunk_total'] = total
        md['chunk_id'] = chunk_ids[i]
        md['prev_chunk_id'] = chunk_ids[i - 1] if i > 0 else None
        md['next_chunk_id'] = chunk_ids[i + 1] if i + 1 < total else None
        d.metadata = md

    return chunks


def _split_documents(documents: List[Document], source_id: str):
    chunks: List[Document] = SPLITTER.split_documents(documents)
    return _with_chunk_ids(chunks, source_id)


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return

    for i, chunk in enumerate(chunks[:5]):
        preview = (chunk.page_content or '')[:300].replace('\n', ' ')
        print(f'[CHUNK {i + 1}]')
        print(f'Sessão: {chunk.metadata.get("session")}')
        print(f'Source: {chunk.metadata.get("source_id")}')
        print(f'Index: {chunk.metadata.get("chunk_index")}/{chunk.metadata.get("chunk_total")}')  # fmt: skip  # noqa: E501
        print(f'ID: {chunk.metadata.get("chunk_id")}')
        print(f'{preview}...')

    anonymizer = PresidioAnonymizer()
    anonymized_chunks = anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_file(full_path: str, vstore: VStore) -> None:
    ext = os.path.splitext(full_path)[1].lower()

    if ext == '.pdf':
        loader = PyMuPDFLoader(full_path, mode='single')
    elif ext == '.docx':
        loader = Docx2txtLoader(full_path)
    elif ext == '.txt':
        loader = TextLoader(full_path, encoding='utf-8')
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    documents = loader.load()
    unique = uuid.uuid5(uuid.NAMESPACE_URL, os.path.abspath(full_path)).hex
    source_id = f'{Path(full_path).name}:{unique}'

    chunks = _split_documents(documents, source_id)
    await _anonymize_and_vectorize(chunks, vstore)


async def create_vectors(file_path: Path, vstore: VStore) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore)
