from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.core.settings import Settings
from iaEditais.events.docs import releases

router = RabbitRouter(url=Settings().BROKER_URL)

router.include_router(releases.router)
