import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import DocumentRelease, User


async def get_users_to_notify(session: AsyncSession, user_ids: list):
    if not user_ids:
        return []
    statement = select(User).where(User.id.in_(user_ids))
    query = await session.scalars(statement)
    return query.all()


def format_release_message(db_release: DocumentRelease):
    db_history = db_release.history
    db_doc = db_history.document

    message_text = (
        f"Olá! O processo de verificação do documento '{db_doc.name}' "
        f'foi concluído com sucesso.'
    )
    return message_text


def prepare_phone_number(user: User):
    if not user.phone_number:
        return None
    phone_number = user.phone_number.strip().replace(' ', '').replace('-', '')
    if not re.fullmatch(r'55\d{10,11}', phone_number):
        return None
    return phone_number
