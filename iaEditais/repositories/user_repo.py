from typing import Optional
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import PasswordReset, User, UserImage
from iaEditais.repositories import util
from iaEditais.schemas import UserFilter


async def get_by_id(session: AsyncSession, user_id: UUID) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_email_or_phone(
    session: AsyncSession, email: str, phone: str = None
) -> Optional[User]:
    conditions = [User.email == email]
    if phone:
        conditions.append(User.phone_number == phone)

    stmt = select(User).where(or_(*conditions))
    return await session.scalar(stmt)


async def get_conflict_user(
    session: AsyncSession, user_id: UUID, email: str, phone: str
) -> Optional[User]:
    stmt = select(User).where(
        User.deleted_at.is_(None),
        User.id != user_id,
        or_(User.email == email, User.phone_number == phone),
    )
    return await session.scalar(stmt)


async def list_all(session: AsyncSession, filters: UserFilter) -> list[User]:
    query = select(User).order_by(User.created_at.desc())

    if filters.unit_id:
        query = query.where(User.unit_id == filters.unit_id)

    if filters.q:
        query = util.apply_text_search(query, User, filters.q, config='simple')

    query = query.offset(filters.offset).limit(filters.limit)
    result = await session.scalars(query)
    return result.all()


async def get_user_image(
    session: AsyncSession, image_id: UUID
) -> Optional[UserImage]:
    return await session.get(UserImage, image_id)


def add_user(session: AsyncSession, user: User) -> None:
    session.add(user)


def add_image(session: AsyncSession, image: UserImage) -> None:
    session.add(image)


def add_password_reset(session: AsyncSession, reset: PasswordReset) -> None:
    session.add(reset)


async def delete_password_reset_by_user(
    session: AsyncSession, user_id: UUID
) -> None:
    await session.execute(
        delete(PasswordReset).where(PasswordReset.user_id == user_id)
    )


async def get_password_reset(
    session: AsyncSession, user_id: UUID
) -> Optional[PasswordReset]:
    return await session.scalar(
        select(PasswordReset).where(PasswordReset.user_id == user_id)
    )


async def delete_entry(session: AsyncSession, entry) -> None:
    await session.delete(entry)
