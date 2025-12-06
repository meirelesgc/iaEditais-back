import os
import re

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_docling.loader import DoclingLoader, ExportType
from langchain_text_splitters import RecursiveCharacterTextSplitter


async def load_document(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'Arquivo não encontrado: {file_path}')

    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.txt':
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        for d in docs:
            d.page_content = clean_text(d.page_content)
            if 'source' not in d.metadata:
                d.metadata['source'] = file_path
        return docs

    else:
        try:
            loader = DoclingLoader(
                file_path=file_path, export_type=ExportType.MARKDOWN
            )
            docs = loader.load()

            for d in docs:
                d.page_content = clean_text(d.page_content)
                if 'source' not in d.metadata:
                    d.metadata['source'] = file_path
            return docs

        except Exception as e:
            raise ValueError(
                f'Erro ao processar arquivo {ext} com Docling: {e}'
            )


def clean_text(text):
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e]', '', text)
    text = text.replace('\x0c', '\n')
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+\n', '\n', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    text = re.sub(r'[ ]{2,}', ' ', text)
    return text.strip()


def parse_with_session(chunks):
    final_chunks: list[Document] = []
    title_pattern = re.compile(r'^\s*(?:[#*]+\s*)?(\d+\.\s+[^\n]+)')

    for chunk in chunks:
        text = chunk.page_content.strip()

        match = title_pattern.match(text)
        if match:
            raw_title = match.group(1).strip()
            session_name = raw_title.replace('*', '').strip()
        else:
            session_name = 'PREÂMBULO DO DOCUMENTO'

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            separators=['\n\n', '\n', ' ', ''],
        )

        subchunks = splitter.split_text(text)

        for subchunk in subchunks:
            formatted_text = (
                f'---\nSESSÃO: {session_name}\n---\n{subchunk.strip()}\n'
            )
            new_chunk = chunk.copy()
            new_chunk.page_content = formatted_text
            if new_chunk.metadata is None:
                new_chunk.metadata = {}
            new_chunk.metadata['session'] = session_name
            final_chunks.append(new_chunk)

    return final_chunks


def split_documents(documents):
    full_text = '\n'.join([doc.page_content for doc in documents])
    regex_pattern = r'(?:\n|^)\s*(?=(?:[#*]+\s*)?\d+\.\s+\S)'

    text_chunks = [
        chunk for chunk in re.split(regex_pattern, full_text) if chunk.strip()
    ]

    base_metadata = documents[0].metadata if documents else {}
    final_chunks = []

    for chunk in text_chunks:
        clean_content = chunk.strip()
        if clean_content:
            final_chunks.append(
                Document(page_content=clean_content, metadata=base_metadata)
            )
    chunks: list[Document] = parse_with_session(final_chunks)
    result = [
        {
            'content': chunk.page_content,
            'session': chunk.metadata.get('session'),
        }
        for chunk in chunks
    ]

    return chunks
