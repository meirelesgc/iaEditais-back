from sqlalchemy import select

from iaEditais.core.dependencies import Session
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentRelease,
    DocumentTypification,
    Typification,
)


async def get_tree_by_release(session: Session, release: DocumentRelease):
    query = await session.scalars(
        select(Typification)
        .join(
            DocumentTypification,
            Typification.id == DocumentTypification.typification_id,
        )
        .join(Document, Document.id == DocumentTypification.document_id)
        .join(DocumentHistory, DocumentHistory.document_id == Document.id)
        .join(
            DocumentRelease, DocumentRelease.history_id == DocumentHistory.id
        )
        .where(
            DocumentRelease.id == release.id,
            Typification.deleted_at.is_(None),
        )
    )
    tree = query.all()
    return tree
