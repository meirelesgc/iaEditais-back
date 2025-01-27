from uuid import UUID
import os
from iaEditais.schemas.Source import Source
from iaEditais.repositories import SourceRepository
from fastapi import UploadFile, HTTPException


def post_source(file: UploadFile):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )

    source = Source(name=file.filename)
    SourceRepository.post_source(source)
    with open(f'storage/sources/{source.id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())
    return source


def get_sources(source_id: UUID):
    sources = SourceRepository.get_source(source_id)
    return sources


def delete_source(source_id: UUID):
    source = SourceRepository.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail='Source not found')

    SourceRepository.delete_source(source_id)
    file_path = f'storage/sources/{source_id}.pdf'
    if os.path.exists(file_path):
        os.remove(file_path)
    return {'message': 'Source deleted successfully'}
