from iaEditais.schemas.doc import (
    CreateDoc,
    Doc,
    Release,
)
import os
from fastapi.responses import FileResponse
from fastapi import UploadFile
from iaEditais.repositories import doc_repository, taxonomy_repository
from iaEditais.integrations import release_integration
from fastapi import HTTPException

from uuid import UUID


def post_doc(doc: CreateDoc):
    doc = Doc(**doc.model_dump())
    doc_repository.post_doc(doc)
    return doc


def get_docs():
    return doc_repository.get_doc()


def get_detailed_doc(doc_id: UUID):
    doc = doc_repository.get_doc(doc_id)
    doc['releases'] = doc_repository.get_releases(doc_id)
    return doc


def delete_doc(doc_id: UUID):
    doc_repository.delete_doc(doc_id)
    return {'message': 'Doc deleted successfully'}


def build_taxonomy(doc_id: UUID):
    taxonomy = taxonomy_repository.get_typification(doc_id=doc_id)
    for typification in taxonomy:
        typification_id = typification.get('id')
        typification['taxonomy'] = taxonomy_repository.get_taxonomy(
            typification_id
        )
        for item in typification['taxonomy']:
            item_id = item.get('id')
            item['branch'] = taxonomy_repository.get_branches(item_id)
    return taxonomy


def post_release(
    doc_id: UUID,
    file: UploadFile,
) -> Release:
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400, detail='Only .pdf files are allowed.'
        )
    release = Release(doc_id=doc_id, taxonomy=build_taxonomy(doc_id))

    with open(f'storage/releases/{release.id}.pdf', 'wb') as buffer:
        buffer.write(file.file.read())
    release_integration.add_to_vector_store(
        f'storage/releases/{release.id}.pdf'
    )
    release = release_integration.analyze_release(release)
    doc_repository.post_release(release)
    return release


def get_releases(doc_id: UUID) -> list[Release]:
    return doc_repository.get_releases(doc_id)


def delete_release(release_id: UUID):
    doc_repository.delete_release(release_id)


def get_release_file(release_id: UUID = None):
    file_path = f'storage/releases/{release_id}.pdf'
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(file_path)
