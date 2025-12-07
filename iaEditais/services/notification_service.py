import re

from faststream.rabbit.fastapi import RabbitBroker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iaEditais.models import DocumentRelease, User


def format_user_welcome_message(username: str, temp_password: str) -> str:
    return (
        f'🚀 Olá, {username}! Seu cadastro em nosso sistema foi concluído com sucesso.'
        f'\n\nSua senha temporária para acesso é: *{temp_password}*'
        f'\n\nPor favor, acesse a plataforma e altere sua senha imediatamente.'
        f'\n\nAtenciosamente, A Equipe.'
    )


async def publish_user_welcome_notification(
    user: User, temp_password: str, broker: RabbitBroker
):
    if not user.phone_number:
        return {'status': 'skipped', 'reason': 'No phone number'}

    message_text = format_user_welcome_message(user.username, temp_password)

    payload = {'user_ids': [user.id], 'message_text': message_text}

    await broker.publish(payload, 'notifications_send_message')

    return {'status': 'published'}


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
