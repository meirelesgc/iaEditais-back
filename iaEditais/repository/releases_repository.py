from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from iaEditais.database import get_session
from iaEditais.models import (
    Document,
    DocumentHistory,
    DocumentRelease,
    DocumentTypification,
    Typification,
    User,
)
from iaEditais.security import get_current_user

Session = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_db_doc(doc_id, session: Session):
    query = (
        select(Document)
        .options(selectinload(Document.history))
        .where(Document.id == doc_id, Document.deleted_at.is_(None))
    )

    db_doc = await session.scalar(query)
    return db_doc


async def insert_db_release(
    latest_history: DocumentHistory,
    file_path: Path,
    session: Session,
    current_user: CurrentUser,
):
    db_release = DocumentRelease(
        history_id=latest_history.id,
        file_path=file_path,
        created_by=current_user.id,
    )

    session.add(db_release)
    await session.commit()
    await session.refresh(db_release)

    return db_release


async def get_check_tree(session: Session, release: DocumentRelease):
    query = await session.scalars(
        select(Typification)
        .join(DocumentTypification)
        .join(Document)
        .join(DocumentHistory)
        .where(
            DocumentHistory.id == release.history_id,
            Typification.deleted_at.is_(None),
        )
    )
    typifications = query.all()
    return {'typifications': typifications}
