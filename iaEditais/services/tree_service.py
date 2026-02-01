from iaEditais.core.dependencies import Session
from iaEditais.models import DocumentRelease
from iaEditais.repositories import tree_repository


async def get_tree_by_release(session: Session, release: DocumentRelease):
    return await tree_repository.get_tree_by_release(session, release)
