import os
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from iaEditais.core.connection import Connection
from iaEditais.models import source_model
from iaEditais.repositories import source_repository


async def source_upload_delete(conn, source_id):
    source = await source_repository.source_get(conn, source_id)
    if not source:
        raise HTTPException(status_code=404, detail='Source not found')

    file_path = f'storage/sources/{source_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')

    os.remove(file_path)

    source = source_model.Source(**source)
    source.has_file = False
    await source_repository.put_source(conn, source)

    return {'message': 'File deleted successfully'}


async def source_put(conn, source):
    source = source_model.Source(**source.model_dump())
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


async def source_post(
    conn: Connection,
    source: source_model.CreateSource,
):
    source = source_model.Source(**source.model_dump())
    await source_repository.souce_post(conn, source)
    return source


async def source_upload_post(
    conn: Connection,
    source_id: int,
    file: UploadFile,
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )

    source = await source_repository.source_get(conn, source_id)
    source = source_model.Source(**source)

    if not source:
        raise HTTPException(status_code=404, detail='Source not found')

    source.has_file = True
    with open(f'storage/sources/{source.id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())

    await source_repository.put_source(conn, source)
    return {'message': 'File uploaded successfully'}


async def source_get(conn, source_id):
    return await source_repository.source_get(conn, source_id)


async def source_delete(conn, source_id: UUID):
    source = await source_repository.source_get(conn, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail='Source not found')
    await source_repository.delete_source(conn, source_id)
    file_path = f'storage/sources/{source_id}.pdf'
    if os.path.exists(file_path):
        os.remove(file_path)
    return {'message': 'Source deleted successfully'}


def source_upload_get(source_id: UUID):
    file_path = f'storage/sources/{source_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)
