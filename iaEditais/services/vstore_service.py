import asyncio
import os
import re
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_docling.loader import DoclingLoader, ExportType

from iaEditais.core.dependencies import VStore
from iaEditais.core.settings import Settings
from iaEditais.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()


def _load_document_sync(file_path: Path):
    if str(file_path).endswith('.txt'):
        loader = TextLoader(str(file_path), encoding='utf-8')
        return loader.load()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4, device=AcceleratorDevice.CPU
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    loader = DoclingLoader(
        file_path=str(file_path),
        export_type=ExportType.MARKDOWN,
        converter=converter,
    )

    return loader.load()


async def load_document(file_path: Path):
    return await asyncio.to_thread(_load_document_sync, file_path)


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
