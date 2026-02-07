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


# fmt: off
def split_documents(documents: list):
    text = '\n'.join([doc.page_content for doc in documents])
    base_metadata = documents[0].metadata.copy() if documents else {}
    pattern = r'(?=\n##\s)'
    chunks_text = [c.strip() for c in re.split(pattern, text) if c.strip()]
    chunks = []
    found_sessions = []
    for chunk in chunks_text:
        match = re.search(r'##\s*(.*)', chunk)
        session_name = match.group(1).strip() if match else 'Preambulo'
        found_sessions.append(session_name)
        metadata = base_metadata.copy()
        metadata['session'] = session_name
        new_doc = Document(page_content=chunk, metadata=metadata)
        chunks.append(new_doc)
    return chunks
# fmt: on


async def _run_standard_pipeline(loader, vstore: VStore):
    documents = loader.load()
    chunks = split_documents(documents)
    presidio_anonymizer = PresidioAnonymizer()
    anonymized_chunks = presidio_anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_pdf(file_path: str, vstore: VStore):
    loader = PyMuPDFLoader(file_path, mode='single')
    await _run_standard_pipeline(loader, vstore)


async def process_docx(file_path: str, vstore: VStore):
    loader = Docx2txtLoader(file_path, mode='single')
    await _run_standard_pipeline(loader, vstore)


async def process_txt(file_path: str, vstore: VStore):
    loader = TextLoader(file_path, encoding='utf-8')
    await _run_standard_pipeline(loader, vstore)


async def create_vectors(file_path: Path, vstore: VStore):
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)

    if not os.path.exists(full_path):
        return

    ext = os.path.splitext(full_path)[1].lower()

    if ext == '.pdf':
        await process_pdf(full_path, vstore)
    elif ext == '.docx':
        await process_docx(full_path, vstore)
    elif ext == '.txt':
        await process_txt(full_path, vstore)
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')
