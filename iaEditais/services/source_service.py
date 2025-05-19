import os
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from iaEditais.core.connection import Connection
from iaEditais.repositories import source_repository
from iaEditais.schemas.source import Source


async def put_source(conn, source: Source):
    source.updated_at = datetime.now()
    await source_repository.put_source(conn, source)
    return source


async def put_source_file(id: UUID, file: UploadFile):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )
    with open(f'storage/sources/{id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())


async def post_source(
    conn: Connection,
    name: str,
    description,
    file: UploadFile,
):
    source = Source(name=name, description=description)

    if file:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400, detail='Only .pdf files are allowed.'
            )
        source.has_file = True
        with open(f'storage/sources/{source.id}.pdf', 'wb') as buffer:
            buffer.write(file.file.read())

    await source_repository.post_source(conn, source)
    return source


async def get_sources(conn):
    return await source_repository.get_source(conn)


async def delete_source(conn, source_id: UUID):
    source = await source_repository.get_source(conn, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail='Source not found')
    await source_repository.delete_source(conn, source_id)
    file_path = f'storage/sources/{source_id}.pdf'
    if os.path.exists(file_path):
        os.remove(file_path)
    return {'message': 'Source deleted successfully'}


def get_source_file(source_id: UUID):
    file_path = f'storage/sources/{source_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)
