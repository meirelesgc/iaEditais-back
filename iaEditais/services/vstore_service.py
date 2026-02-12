import os
import re
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
    chunk_size=500,
    chunk_overlap=50,
)


def _clean_and_format_documents(documents: List[Document]) -> List[Document]:
    chunks = SPLITTER.split_documents(documents)

    for i, chunk in enumerate(chunks):
        text = re.sub(r'\s+', ' ', (chunk.page_content or '')).strip()
        section = (chunk.metadata.get('section_title') or '').strip()

        if section:
            chunk.page_content = f'SECTION: {section}\n\n{text}'
        else:
            chunk.page_content = text

        chunk.metadata['chunk_index'] = i

        if 'source' not in chunk.metadata:
            chunk.metadata['source'] = 'unknown'

    return chunks


def _split_by_sections(documents: List[Document]) -> List[Document]:
    split_documents = []

    # Não mexe no caractere estranho
    section_pattern = r'(^\d+\s*[\.\-–]\s*(?!\d)\S.{0,49}$)'

    for doc in documents:
        parts = re.split(section_pattern, doc.page_content, flags=re.MULTILINE)

        if parts[0].strip():
            meta = doc.metadata.copy()
            meta['section_title'] = 'Introdução'
            split_documents.append(
                Document(page_content=parts[0], metadata=meta)
            )

        for i in range(1, len(parts), 2):
            header = parts[i].strip()
            content = parts[i + 1] if i + 1 < len(parts) else ''
            full_content = f'{header}\n{content}'
            meta = doc.metadata.copy()
            meta['section_title'] = header
            split_documents.append(
                Document(page_content=full_content, metadata=meta)
            )
    return split_documents


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return

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

    raw_documents = loader.load()

    section_documents = _split_by_sections(raw_documents)

    formatted_documents = _clean_and_format_documents(section_documents)

    await _anonymize_and_vectorize(formatted_documents, vstore)


async def create_vectors(file_path: Path, vstore: VStore) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore)
