import asyncio
import os
import re
from pathlib import Path

from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document

from iaEditais.core.dependencies import VStore
from iaEditais.core.settings import Settings
from iaEditais.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()


async def load_document(file_path: Path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        loader = PyMuPDFLoader(file_path, mode='single')
    elif ext == '.docx':
        loader = Docx2txtLoader(file_path, mode='single')
    elif ext == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    return loader.load()


def split_documents(documents: list):
    text = '\n'.join([doc.page_content for doc in documents])
    base_metadata = documents[0].metadata.copy() if documents else {}
    pattern = r'(?=\n##\s)'
    chunks_text = [c.strip() for c in re.split(pattern, text) if c.strip()]
    chunks = []
    for chunk in chunks_text:
        match = re.search(r'##\s*(.*)', chunk)
        session = match.group(1).strip() if match else 'Preambulo'
        metadata = base_metadata.copy()
        metadata['session'] = session
        new_doc = Document(page_content=chunk, metadata=metadata)
        chunks.append(new_doc)
    return chunks


async def create_vectors(file_path: Path, vstore: VStore):
    unique_filename = file_path.split('/')[-1]
    file_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(file_path):
        return ...

    documents = await load_document(file_path)
    chunks = split_documents(documents)

    presidio_anonymizer = PresidioAnonymizer()

    anonymized_chunks = await asyncio.to_thread(
        presidio_anonymizer.anonymize_chunks, chunks, verbose=False
    )

    await vstore.aadd_documents(anonymized_chunks)
