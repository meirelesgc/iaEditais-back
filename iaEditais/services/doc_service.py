import os
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse

from iaEditais.core.connection import Connection
from iaEditais.integrations import release_integration
from iaEditais.repositories import doc_repository, taxonomy_repository
from iaEditais.schemas.doc import CreateDoc, Doc, Release


async def post_doc(conn: Connection, doc: CreateDoc):
    doc = Doc(**doc.model_dump())
    if len(doc.typification) < 1:
        raise HTTPException(
            status_code=400, detail='At least one typification must be selected.'
        )
    await doc_repository.post_doc(conn, doc)
    return doc


async def get_docs(conn: Connection):
    return await doc_repository.get_doc(conn)


def get_detailed_doc(conn: Connection, doc_id: UUID):
    doc = doc_repository.get_doc(conn, doc_id)
    doc['releases'] = doc_repository.get_releases(conn, doc_id)
    return doc


async def delete_doc(conn: Connection, doc_id: UUID):
    await doc_repository.delete_doc(conn, doc_id)
    return {'message': 'Doc deleted successfully'}


async def build_verification_tree(conn: Connection, doc_id: UUID):
    taxonomy = await taxonomy_repository.get_typification(conn, doc_id=doc_id)
    for typification in taxonomy:
        typification_id = typification.get('id')
        typification['taxonomy'] = await taxonomy_repository.get_taxonomy(
            conn, typification_id
        )
        for item in typification['taxonomy']:
            item_id = item.get('id')
            item['branch'] = await taxonomy_repository.get_branches(
                conn, item_id
            )
    return taxonomy


async def post_release(
    conn: Connection,
    doc_id: UUID,
    file: UploadFile,
) -> Release:
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )
    tx = await build_verification_tree(conn, doc_id)
    release = Release(doc_id=doc_id, taxonomy=tx)

    with open(f'storage/releases/{release.id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())

    release_integration.add_to_vector_store(f'storage/releases/{release.id}.pdf')
    release = release_integration.analyze_release(release)
    await doc_repository.post_release(conn, release)
    return release


async def get_releases(conn: Connection, doc_id: UUID) -> list[Release]:
    return await doc_repository.get_releases(conn, doc_id)


async def delete_release(conn: Connection, release_id: UUID):
    await doc_repository.delete_release(conn, release_id)


def get_release_file(release_id: UUID = None):
    file_path = f'storage/releases/{release_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)
