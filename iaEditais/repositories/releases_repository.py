from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.database import get_session
from iaEditais.core.security import get_current_user
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentRelease,
    DocumentTypification,
    Typification,
    User,
)

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_db_doc(doc_id, session: Session):
    query = select(Document).where(
        Document.id == doc_id, Document.deleted_at.is_(None)
    )

    db_doc = await session.scalar(query)
    return db_doc


async def insert_db_release(
    latest_history: DocumentHistory,
    file_path: str | Path,
    session: Session,
    current_user: CurrentUser,
    is_test: bool = False,
):
    # Converte para string se for Path (o banco espera string)
    file_path_str = str(file_path) if isinstance(file_path, Path) else file_path
    
    db_release = DocumentRelease(
        history_id=latest_history.id,
        file_path=file_path_str,
        created_by=current_user.id,
        is_test=is_test,
    )

    session.add(db_release)
    await session.commit()
    await session.refresh(db_release)

    return db_release


async def get_check_tree(session: Session, release: DocumentRelease):
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
    return query.all()


async def save_description(
    session: Session, release: DocumentRelease, description: str
):
    release.description = description
    await session.commit()
    await session.refresh(release)
    return release
