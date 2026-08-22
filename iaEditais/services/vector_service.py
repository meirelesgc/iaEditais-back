import os
import re
from pathlib import Path
from typing import List

import fitz
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

HEADER_RE = re.compile(r'^\d+\s*[\.\-–]\s*(?!\d)\S.{0,49}$')


def _clean_and_format_documents(documents: List[Document]) -> List[Document]:
    chunks = SPLITTER.split_documents(documents)

    for i, chunk in enumerate(chunks):
        text = chunk.page_content or ''
        text = text.replace('\x00', '')
        text = re.sub(r'\s+', ' ', text).strip()
        section = (chunk.metadata.get('section_title') or '').strip()
        if section:
            chunk.page_content = f'SECTION: {section}\n\n{text}'
        else:
            chunk.page_content = text
        chunk.metadata['chunk_index'] = i
        chunk.metadata.setdefault('source', 'unknown')
        chunk.metadata['chunk_id'] = f"chunk_{i}"
        chunk.metadata.setdefault('page', 0)
        chunk.metadata.setdefault('rects', [])
    return chunks


def _split_by_sections(documents: List[Document]) -> List[Document]:
    split_documents = []
    # Regex sensível mantido
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


class CoordinateChunker:
    """Agrupa palavras do PDF em chunks <= max_chars preservando
    as coordenadas (bounding box) de cada linha física."""

    def __init__(self, max_chars=500):
        self.max_chars = max_chars

    def process_page(self, doc, page_num) -> List[dict]:
        page = doc[page_num]
        words = page.get_text('words')
        chunks = []
        current_chunk_text = ''
        current_chunk_lines = []
        current_chunk_rects = []
        current_line_key = None
        line_words = []

        def process_line(l_words):
            nonlocal current_chunk_text
            nonlocal current_chunk_lines
            nonlocal current_chunk_rects
            if not l_words:
                return
            lx0 = min(w[0] for w in l_words)
            ly0 = min(w[1] for w in l_words)
            lx1 = max(w[2] for w in l_words)
            ly1 = max(w[3] for w in l_words)
            line_text = ' '.join(w[4] for w in l_words)

            if (
                len(current_chunk_text) + len(line_text) + 1 > self.max_chars
                and current_chunk_text
            ):
                chunks.append({
                    'page': page_num,
                    'text': current_chunk_text.strip(),
                    'lines': list(current_chunk_lines),
                    'rects': list(current_chunk_rects),
                })
                current_chunk_text = line_text + ' '
                current_chunk_lines = [line_text]
                current_chunk_rects = [[lx0, ly0, lx1, ly1]]
            else:
                current_chunk_text += line_text + ' '
                current_chunk_lines.append(line_text)
                current_chunk_rects.append([lx0, ly0, lx1, ly1])

        for w in words:
            key = (w[5], w[6])
            if current_line_key != key:
                if current_line_key is not None:
                    process_line(line_words)
                current_line_key = key
                line_words = []
            line_words.append(w)

        if line_words:
            process_line(line_words)

        if current_chunk_text:
            chunks.append({
                'page': page_num,
                'text': current_chunk_text.strip(),
                'lines': list(current_chunk_lines),
                'rects': list(current_chunk_rects),
            })

        return chunks


def _extract_pdf_documents(full_path: str, source_name: str) -> List[Document]:
    doc = fitz.open(full_path)
    chunker = CoordinateChunker(max_chars=500)

    raw_chunks: List[dict] = []
    for i in range(len(doc)):
        raw_chunks.extend(chunker.process_page(doc, i))
    doc.close()

    documents = []
    current_section = ''
    for gi, c in enumerate(raw_chunks):
        for line in c['lines']:
            stripped = line.strip()
            if HEADER_RE.match(stripped):
                current_section = stripped

        text = c['text'].replace('\x00', '')
        text = re.sub(r'\s+', ' ', text).strip()
        if not text:
            continue

        metadata = {
            'chunk_id': f'chunk_{gi}',
            'chunk_index': gi,
            'page': c['page'],
            'rects': c['rects'],
            'source': source_name,
            'section_title': current_section,
        }
        if current_section:
            content = f'SECTION: {current_section}\n\n{text}'
        else:
            content = text
        documents.append(Document(page_content=content, metadata=metadata))

    return documents


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return
    anonymizer = PresidioAnonymizer()
    anonymized_chunks = anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_file(full_path: str, vstore: VStore) -> None:
    ext = os.path.splitext(full_path)[1].lower()
    source_name = f'iaEditais/storage/uploads/{os.path.basename(full_path)}'

    if ext == '.pdf':
        formatted_documents = _extract_pdf_documents(full_path, source_name)
    elif ext == '.docx':
        loader = Docx2txtLoader(full_path)
        raw_documents = loader.load()
        section_documents = _split_by_sections(raw_documents)
        formatted_documents = _clean_and_format_documents(section_documents)
        for doc in formatted_documents:
            doc.metadata['source'] = source_name
    elif ext == '.txt':
        loader = TextLoader(full_path, encoding='utf-8')
        raw_documents = loader.load()
        section_documents = _split_by_sections(raw_documents)
        formatted_documents = _clean_and_format_documents(section_documents)
        for doc in formatted_documents:
            doc.metadata['source'] = source_name
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    await _anonymize_and_vectorize(formatted_documents, vstore)


async def create_vectors(file_path: Path, vstore: VStore) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore)
