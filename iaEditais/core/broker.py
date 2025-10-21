from faststream.rabbit import fastapi

from iaEditais.core.settings import Settings

settings = Settings()

router = fastapi.RabbitRouter(settings.BROKER_URL)


def get_broker():
    return router.broker
