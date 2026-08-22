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

MAX_CHARS_PER_CHUNK = 500
SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=MAX_CHARS_PER_CHUNK,
    chunk_overlap=50,
)


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


def _load_pdf_lines(full_path: str) -> list[tuple[int, str, list]]:
    lines_with_pages: list[tuple[int, str, list]] = []
    with fitz.open(full_path) as pdf:
        for page_num in range(len(pdf)):
            for line_text, rect in _extract_page_lines(pdf[page_num]):
                normalized = re.sub(r'\s+', ' ', line_text).strip()
                if normalized:
                    lines_with_pages.append((page_num, normalized, rect))
    return lines_with_pages


def _attach_pdf_coordinates(chunks: List[Document], full_path: str) -> None:
    """Mapeia o texto de cada chunk de volta às linhas do PDF para
    preencher 'page' e 'rects' sem alterar o conteúdo produzido pelo
    pipeline original (loader -> seções -> splitter)."""
    stream: list[tuple[str, int, list]] = []
    for page_num, line_text, _rect in _load_pdf_lines(full_path):
        for token in line_text.split():
            stream.append((token.lower(), page_num, _rect))

    # overlap do splitter faz o chunk seguinte repetir palavras do
    # anterior; a janela permite remachar esse trecho sem quebrar a
    # progressão monotônica do cursor.
    overlap_window = max(40, SPLITTER.chunk_overlap * 3)

    cursor = 0
    for doc in chunks:
        content = doc.page_content or ''
        body = content
        if body.startswith('SECTION:') and '\n\n' in body:
            body = body.split('\n\n', 1)[1]
        needed = re.sub(r'\s+', ' ', body).strip().lower().split()
        if not needed:
            continue

        matched_rects: list[list] = []
        first_new_page = None
        last_matched_page = None
        old_cursor = cursor
        j = max(0, cursor - overlap_window)
        ok = True
        for token in needed:
            while j < len(stream) and stream[j][0] != token:
                j += 1
            if j >= len(stream):
                ok = False
                break
            _, page_num, rect = stream[j]
            last_matched_page = page_num
            if j >= old_cursor and first_new_page is None:
                first_new_page = page_num
            target_page = first_new_page or last_matched_page
            if page_num == target_page and (
                not matched_rects or matched_rects[-1] != rect
            ):
                matched_rects.append(rect)
            j += 1

        if ok:
            doc.metadata['page'] = first_new_page or last_matched_page
            doc.metadata['rects'] = matched_rects
            if j > cursor:
                cursor = j


def _pdf_to_documents(full_path: str) -> List[Document]:
    loader = PyMuPDFLoader(full_path, mode='single')
    raw_documents = loader.load()

    section_documents = _split_by_sections(raw_documents)
    chunks = _clean_and_format_documents(section_documents)

    # normaliza o source para o formato esperado pelos filtros de busca
    canonical_source = (
        f'iaEditais/storage/uploads/{os.path.basename(full_path)}'
    )
    for chunk in chunks:
        chunk.metadata['source'] = canonical_source

    _attach_pdf_coordinates(chunks, full_path)
    return chunks


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
