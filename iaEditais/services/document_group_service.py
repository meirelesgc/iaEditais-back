from http import HTTPStatus
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.core.dependencies import Storage
from iaEditais.core.storage_provider import is_valid_image_filename
from iaEditais.models import DocumentGroup, DocumentGroupItem
from iaEditais.repositories import document_group_repo
from iaEditais.schemas.document_group import (
    DocumentGroupCreate,
    DocumentGroupFilter,
    DocumentGroupItemCreate,
    DocumentGroupItemUpdate,
    DocumentGroupPublic,
    DocumentGroupUpdate,
)
from iaEditais.services import audit_service


async def create_group(
    session: AsyncSession, user_id: UUID, data: DocumentGroupCreate
) -> DocumentGroup:
    existing = await document_group_repo.get_by_name(session, data.name)
    if existing:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Document group name already exists',
        )

    db_group = DocumentGroup(name=data.name)
    db_group.set_creation_audit(user_id)

    document_group_repo.add_group(session, db_group)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='CREATE',
        table_name=DocumentGroup.__tablename__,
        record_id=db_group.id,
        old_data=None,
    )

    await session.commit()
    await session.refresh(db_group)
    return db_group


async def get_groups(
    session: AsyncSession, filters: DocumentGroupFilter
) -> list[DocumentGroup]:
    return await document_group_repo.list_all(session, filters)


async def get_group_by_id(
    session: AsyncSession, group_id: UUID
) -> DocumentGroup:
    group = await document_group_repo.get_by_id(session, group_id)
    if not group or group.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group not found',
        )
    return group


async def update_group(
    session: AsyncSession, user_id: UUID, data: DocumentGroupUpdate
) -> DocumentGroup:
    db_group = await document_group_repo.get_by_id(session, data.id)
    if not db_group or db_group.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group not found',
        )

    old_data = DocumentGroupPublic.model_validate(db_group).model_dump(mode='json')

    conflict = await document_group_repo.get_by_name(
        session, data.name, exclude_id=data.id
    )
    if conflict:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail='Document group name already exists',
        )

    db_group.name = data.name
    db_group.set_update_audit(user_id)
    await session.flush()
    await session.refresh(db_group)

    new_data = DocumentGroupPublic.model_validate(db_group).model_dump(mode='json')

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='UPDATE',
        table_name=DocumentGroup.__tablename__,
        record_id=db_group.id,
        old_data=old_data,
        new_data=new_data,
    )

    await session.commit()
    await session.refresh(db_group)
    return db_group


async def delete_group(
    session: AsyncSession, user_id: UUID, group_id: UUID
) -> None:
    db_group = await document_group_repo.get_by_id(session, group_id)
    if not db_group or db_group.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group not found',
        )

    old_data = DocumentGroupPublic.model_validate(db_group).model_dump(mode='json')
    db_group.set_deletion_audit(user_id)

    await audit_service.register_action(
        session=session,
        user_id=user_id,
        action='DELETE',
        table_name=DocumentGroup.__tablename__,
        record_id=db_group.id,
        old_data=old_data,
    )

    await session.commit()


async def create_item(
    session: AsyncSession, user_id: UUID, group_id: UUID, data: DocumentGroupItemCreate
) -> DocumentGroupItem:
    group = await document_group_repo.get_by_id(session, group_id)
    if not group or group.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group not found',
        )

    db_item = DocumentGroupItem(group_id=group_id, name=data.name)
    db_item.set_creation_audit(user_id)

    document_group_repo.add_item(session, db_item)

    await session.commit()
    await session.refresh(db_item)
    return db_item


async def update_item(
    session: AsyncSession, user_id: UUID, data: DocumentGroupItemUpdate
) -> DocumentGroupItem:
    db_item = await document_group_repo.get_item_by_id(session, data.id)
    if not db_item or db_item.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item not found',
        )

    db_item.name = data.name
    db_item.set_update_audit(user_id)

    await session.commit()
    await session.refresh(db_item)
    return db_item


async def update_item_icon(
    session: AsyncSession,
    user_id: UUID,
    item_id: UUID,
    file: UploadFile,
    storage: Storage,
) -> DocumentGroupItem:
    db_item = await document_group_repo.get_item_by_id(session, item_id)
    if not db_item or db_item.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item not found',
        )

    if not is_valid_image_filename(file.filename):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail='Invalid file format'
        )

    if db_item.icon_path:
        await storage.delete(db_item.icon_path)

    unique_filename = f'{uuid4()}_{file.filename}'
    db_item.icon_path = await storage.save(file, unique_filename)
    db_item.set_update_audit(user_id)

    await session.commit()
    await session.refresh(db_item)
    return db_item


async def delete_item_icon(
    session: AsyncSession, user_id: UUID, item_id: UUID, storage: Storage
) -> None:
    db_item = await document_group_repo.get_item_by_id(session, item_id)
    if not db_item or db_item.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item not found',
        )

    if not db_item.icon_path:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item has no icon',
        )

    await storage.delete(db_item.icon_path)
    db_item.icon_path = None
    db_item.set_update_audit(user_id)

    await session.commit()


async def delete_item(
    session: AsyncSession, user_id: UUID, item_id: UUID
) -> None:
    db_item = await document_group_repo.get_item_by_id(session, item_id)
    if not db_item or db_item.deleted_at:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail='Document group item not found',
        )

    db_item.set_deletion_audit(user_id)
    await session.commit()
