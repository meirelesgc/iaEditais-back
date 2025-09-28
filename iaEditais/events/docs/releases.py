from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.core.dependencies import Model, Session, VStore
from iaEditais.core.settings import Settings
from iaEditais.services import releases_service

router = RabbitRouter(Settings().BROKER_URL)


@router.subscriber('process_release')
async def process_release(
    release: dict,
    model: Model,
    session: Session,
    vectorstore: VStore,
):
    await releases_service.process_release(
        model, session, vectorstore, release
    )
    return {'response': 'Hello, Rabbit!'}
