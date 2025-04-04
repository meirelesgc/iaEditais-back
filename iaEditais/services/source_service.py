from uuid import UUID
from fastapi.responses import FileResponse
import os
from iaEditais.schemas.source import Source
from iaEditais.repositories import source_repository
from fastapi import UploadFile, HTTPException


def post_source(name: str, description, file: UploadFile):
    names = [s['name'] for s in source_repository.get_source(name=name)]

    if name in names:
        raise HTTPException(
            status_code=409, detail=f'Source {name} already exists.'
        )

    source = Source(name=name, description=description)

    if file:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400, detail='Only .pdf files are allowed.'
            )
        source.has_file = True
        with open(f'storage/sources/{source.id}.pdf', 'wb') as buffer:
            buffer.write(file.file.read())

    source_repository.post_source(source)
    return source


def get_sources():
    return source_repository.get_source()


def delete_source(source_id: UUID):
    source = source_repository.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail='Source not found')
    source_repository.delete_source(source_id)
    file_path = f'storage/sources/{source_id}.pdf'
    if os.path.exists(file_path):
        os.remove(file_path)
    return {'message': 'Source deleted successfully'}


def get_source_file(source_id: UUID):
    file_path = f'storage/sources/{source_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)
