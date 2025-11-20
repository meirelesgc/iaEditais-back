from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.core.settings import Settings

settings = Settings()

router = RabbitRouter(settings.BROKER_URL)


def get_broker():  # pragma: no cover
    return router.broker
