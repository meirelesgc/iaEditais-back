import re

from iaEditais.core.dependencies import Session
from iaEditais.models import DocumentRelease, User
from iaEditais.workers.utils import send_message


async def publish_password_reset_notification(
    user: User, reset_token: str, session: Session
):
    if not user.phone_number:
        return {'status': 'skipped', 'reason': 'No phone number'}

    message_text = (
        f'Olá, {user.username}. '
        f'Seu código para redefinir a senha é: *{reset_token}*. '
        'Este código expira em 15 minutos. '
        'Se não foi você que solicitou, ignore esta mensagem.'
    )

    payload = {'user_ids': [user.id], 'message_text': message_text}

    await send_message(payload, session)

    return {'status': 'published'}


def format_user_welcome_message(username: str, temp_password: str) -> str:
    return (
        f'🚀 Olá, {username}! Seu cadastro em nosso sistema foi concluído com sucesso.'
        f'\n\nSua senha temporária para acesso é: *{temp_password}*'
        f'\n\nPor favor, acesse a plataforma e altere sua senha imediatamente.'
        f'\n\nAtenciosamente, A Equipe.'
    )


async def publish_user_welcome_notification(
    user: User, temp_password: str, session: Session
):
    if not user.phone_number:
        return {'status': 'skipped', 'reason': 'No phone number'}

    message_text = format_user_welcome_message(user.username, temp_password)

    payload = {'user_ids': [user.id], 'message_text': message_text}

    await send_message(payload, session)

    return {'status': 'published'}


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


async def publish_test_whatsapp_notification(user: User, session: Session):
    clean_number = prepare_phone_number(user)

    if not clean_number:
        return {
            'status': 'error',
            'detail': 'Invalid phone format. Must be 55 + DDD + Number (10-11 digits).',
        }

    message_text = (
        f'🤖 Olá, {user.username}! \n\n'
        f'Este é um teste de verificação do seu número no iaEditais. '
        f'Se você recebeu esta mensagem, seu cadastro está correto.'
    )

    payload = {'user_ids': [user.id], 'message_text': message_text}

    await send_message(payload, session)

    return {'status': 'published', 'detail': 'Test message queued'}
