from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Document, Project, ProjectDocument
from iaEditais.schemas.project import ProjectFilter


async def get_by_id(
    session: AsyncSession, project_id: UUID
) -> Optional[Project]:
    return await session.get(Project, project_id)


async def get_by_name(
    session: AsyncSession, name: str, exclude_id: Optional[UUID] = None
) -> Optional[Project]:
    stmt = select(Project).where(
        Project.deleted_at.is_(None), Project.name == name
    )
    if exclude_id:
        stmt = stmt.where(Project.id != exclude_id)
    return await session.scalar(stmt)


async def list_all(
    session: AsyncSession, filters: ProjectFilter
) -> list[Project]:
    query = (
        select(Project)
        .where(Project.deleted_at.is_(None))
        .order_by(Project.created_at.desc())
    )

    if filters.q:
        query = query.where(Project.name.ilike(f'%{filters.q}%'))

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


def add_project(session: AsyncSession, project: Project) -> None:
    session.add(project)


async def update_document_project_names(
    session: AsyncSession,
    project_id: UUID,
    old_name: str,
    new_name: str,
) -> None:
    project_document_ids = select(ProjectDocument.id).where(
        ProjectDocument.project_id == project_id
    )
    await session.execute(
        update(Document)
        .where(
            or_(
                Document.projeto_nome == old_name,
                Document.project_document_id.in_(project_document_ids),
            )
        )
        .values(projeto_nome=new_name)
    )
