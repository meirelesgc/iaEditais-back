import os
import re
from pathlib import Path
from typing import List

import fitz
from langchain_community.document_loaders import (
    Docx2txtLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from iaEditais.core.dependencies import VStore
from iaEditais.core.settings import Settings
from iaEditais.utils.PresidioAnonymizer import PresidioAnonymizer

SETTINGS = Settings()

SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)

SECTION_PATTERN = re.compile(r'^\d+\s*[\.\-–]\s*(?!\d)\S.{0,49}$')
MAX_CHARS_PER_CHUNK = 1500
CHUNK_OVERLAP_CHARS = 250


def _extract_page_lines(page) -> list[tuple[str, list]]:
    lines: dict[tuple[int, int], list] = {}
    for word in page.get_text('words'):
        key = (word[5], word[6])
        lines.setdefault(key, []).append(word)

    extracted = []
    for key in sorted(lines):
        words = sorted(lines[key], key=lambda w: w[0])
        rect = [
            min(w[0] for w in words),
            min(w[1] for w in words),
            max(w[2] for w in words),
            max(w[3] for w in words),
        ]
        text = ' '.join(w[4] for w in words)
        extracted.append((text, rect))
    return extracted


def _pdf_to_documents(full_path: str) -> List[Document]:
    source_name = (
        f'iaEditais/storage/uploads/{os.path.basename(full_path)}'
    )
    documents: List[Document] = []
    page_counts: dict[int, int] = {}
    buffer: list[tuple[str, list]] = []
    buffer_page = 0
    buffer_len = 0
    current_section = ''

    def flush_buffer(keep_overlap: bool = False):
        nonlocal buffer, buffer_len
        if not buffer:
            return
        joined = ' '.join(line for line, _ in buffer)
        text = re.sub(r'\s+', ' ', joined.replace('\x00', '')).strip()
        rects = [rect for _, rect in buffer]
        page = buffer_page
        snapshot = buffer

        if keep_overlap:
            tail: list[tuple[str, list]] = []
            for line_text, rect in reversed(snapshot):
                candidate_text = ' '.join(
                    [line_text] + [l for l, _ in tail]
                )
                if len(candidate_text) > CHUNK_OVERLAP_CHARS:
                    break
                tail.insert(0, (line_text, rect))
            # nunca reutilizar o buffer inteiro (geraria chunk duplicado)
            while tail and len(tail) == len(snapshot):
                tail = tail[1:]
            buffer = tail
            buffer_len = sum(len(l) for l, _ in buffer) + max(
                0, len(buffer) - 1
            )
        else:
            buffer = []
            buffer_len = 0

        if not text:
            return
        content = text
        if current_section:
            content = f'SECTION: {current_section}\n\n{text}'
        count = page_counts.get(page, 0)
        page_counts[page] = count + 1
        documents.append(
            Document(
                page_content=content,
                metadata={
                    'chunk_id': f'chunk_{page}_{count}',
                    'chunk_index': len(documents),
                    'page': page,
                    'rects': rects,
                    'source': source_name,
                },
            )
        )

    with fitz.open(full_path) as pdf:
        for page_num in range(len(pdf)):
            for line_text, rect in _extract_page_lines(pdf[page_num]):
                line = line_text.strip()
                if not line:
                    continue
                is_header = bool(SECTION_PATTERN.match(line))
                page_changed = bool(buffer) and buffer_page != page_num
                overflow = bool(buffer) and (
                    buffer_len + 1 + len(line) > MAX_CHARS_PER_CHUNK
                )
                if is_header or page_changed:
                    flush_buffer()
                elif overflow:
                    # overlap só no corte por tamanho: preserva a
                    # continuidade do texto entre chunks consecutivos
                    flush_buffer(keep_overlap=True)
                if is_header:
                    current_section = line
                if not buffer:
                    buffer_page = page_num
                buffer.append((line, rect))
                buffer_len += len(line) + (1 if buffer_len else 0)
        flush_buffer()

    return documents


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


async def _anonymize_and_vectorize(chunks: List[Document], vstore: VStore):
    if not chunks:
        return
    anonymizer = PresidioAnonymizer()
    anonymized_chunks = anonymizer.anonymize_chunks(chunks)
    await vstore.aadd_documents(anonymized_chunks)


async def process_file(full_path: str, vstore: VStore) -> None:
    ext = os.path.splitext(full_path)[1].lower()

    if ext == '.pdf':
        formatted_documents = _pdf_to_documents(full_path)
    elif ext == '.docx':
        loader = Docx2txtLoader(full_path)
        raw_documents = loader.load()
        section_documents = _split_by_sections(raw_documents)
        formatted_documents = _clean_and_format_documents(section_documents)
    elif ext == '.txt':
        loader = TextLoader(full_path, encoding='utf-8')
        raw_documents = loader.load()
        section_documents = _split_by_sections(raw_documents)
        formatted_documents = _clean_and_format_documents(section_documents)
    else:
        raise ValueError(f'Tipo de arquivo não suportado: {ext}')

    await _anonymize_and_vectorize(formatted_documents, vstore)


async def create_vectors(file_path: Path, vstore: VStore) -> None:
    unique_filename = str(file_path).split('/')[-1]
    full_path = os.path.join(SETTINGS.UPLOAD_DIRECTORY, unique_filename)
    if not os.path.exists(full_path):
        return
    await process_file(full_path, vstore)
