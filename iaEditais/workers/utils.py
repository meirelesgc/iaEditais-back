import httpx
from faststream.rabbit import RabbitRouter
from sqlalchemy import select

from iaEditais.core.dependencies import Session
from iaEditais.core.settings import Settings
from iaEditais.models import User
from iaEditais.services import notification_service

SETTINGS = Settings()
URL = SETTINGS.EVOLUTION_URL
UPLOAD_DIRECTORY = 'iaEditais/storage/uploads'
BROKER_URL = SETTINGS.BROKER_URL
HEADERS = {
    'Content-Type': 'application/json',
    'apikey': SETTINGS.EVOLUTION_KEY,
}


router = RabbitRouter()


@router.subscriber('send_message')
async def send_message(payload: dict, session: Session):
    user_ids = payload.get('user_ids', [])
    message_text = payload.get('message_text')

    if not user_ids or not message_text:
        pass  # WIP

    statement = select(User).where(User.id.in_(user_ids))
    query = await session.scalars(statement)
    users_to_notify = query.all()

    async with httpx.AsyncClient() as client:
        for user in users_to_notify:
            phone_number = notification_service.prepare_phone_number(user)

            if not phone_number:
                continue

            payload = {'number': phone_number, 'text': message_text}
            await client.post(URL, headers=HEADERS, json=payload)
