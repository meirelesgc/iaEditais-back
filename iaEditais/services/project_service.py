from http import HTTPStatus
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import Project
from iaEditais.repositories import project_repo
from iaEditais.schemas.project import (
    ProjectCreate,
    ProjectFilter,
    ProjectPublic,
    ProjectUpdate,
)
from iaEditais.services import audit_service


async def create_project(
    session: AsyncSession, user_id: UUID, data: ProjectCreate
) -> Project:
    existing = await project_repo.get_by_name(session, data.name)
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Já existe um projeto com esse nome.',
        )

    db_project = Project(
        name=data.name,
        description=data.description,
        document_group_id=data.document_group_id,
    )
    db_project.set_creation_audit(user_id)

    project_repo.add_project(session, db_project)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=Project.__tablename__,
        record_id=db_project.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_project)
    return db_project


async def get_projects(
    session: AsyncSession, filters: ProjectFilter
) -> list[Project]:
    return await project_repo.list_all(session, filters)


async def get_project_by_id(
    session: AsyncSession, project_id: UUID
) -> Project:
    project = await project_repo.get_by_id(session, project_id)
    if not project or project.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Project not found',
        )
    return project


async def update_project(
    session: AsyncSession, user_id: UUID, data: ProjectUpdate
) -> Project:
    db_project = await project_repo.get_by_id(session, data.id)
    if not db_project or db_project.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Project not found',
        )

    old_data = ProjectPublic.model_validate(db_project).model_dump(mode='json')
    old_name = db_project.name

    if data.name != old_name:
        conflict = await project_repo.get_by_name(
            session, data.name, exclude_id=data.id
        )
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail='Já existe um projeto com esse nome.',
            )

    db_project.name = data.name
    db_project.description = data.description
    db_project.document_group_id = data.document_group_id
    if data.status is not None:
        db_project.status = data.status

    new_data = ProjectPublic.model_validate(db_project).model_dump(mode='json')

    db_project.set_update_audit(user_id)

    if data.name != old_name:
        await project_repo.update_document_project_names(
            session, data.id, old_name, data.name
        )

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=Project.__tablename__,
        record_id=db_project.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_project)
    return db_project


async def delete_project(
    session: AsyncSession, user_id: UUID, project_id: UUID
) -> None:
    db_project = await project_repo.get_by_id(session, project_id)
    if not db_project or db_project.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Project not found',
        )

    old_data = ProjectPublic.model_validate(db_project).model_dump(mode='json')
    db_project.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=Project.__tablename__,
        record_id=db_project.id,
        old_data=old_data,
    )

    await session.commit()
