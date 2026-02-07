import os
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


def _simple_split(documents: List[Document]) -> List[Document]:
    if not documents:
        return []

    full_text = '\n'.join([d.page_content for d in documents])
    base_metadata = documents[0].metadata.copy()
    base_metadata['session'] = 'Preambulo'
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=100, separators=['\n\n', '\n', ' ', '']
    )
    text_chunks = splitter.split_text(full_text)
    final_chunks = []
    for content in text_chunks:
        doc = Document(page_content=content, metadata=base_metadata)
        final_chunks.append(doc)
    return final_chunks


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return

    for i, chunk in enumerate(chunks[:3]):
        preview = chunk.page_content[:150].replace('\n', ' ')
        print(f'[CHUNK {i + 1}]')
        print(f'Sessão: {chunk.metadata.get("session")}')
        print(f'{preview}...')

    presidio_anonymizer = PresidioAnonymizer()
    anonymized_chunks = presidio_anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_generic_pipeline(loader, vstore: VStore):
    documents = loader.load()
    chunks = _simple_split(documents)
    await _anonymize_and_vectorize(chunks, vstore)


async def create_vectors(file_path: Path, vstore: VStore):
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    ext = os.path.splitext(full_path)[1].lower()

    match ext:
        case '.pdf':
            loader = PyMuPDFLoader(full_path)
        case '.docx':
            loader = Docx2txtLoader(full_path)
        case '.txt':
            loader = TextLoader(full_path, encoding='utf-8')
        case _:
            raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    await process_generic_pipeline(loader, vstore)
