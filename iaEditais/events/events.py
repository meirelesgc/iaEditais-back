from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.core.settings import Settings
from iaEditais.events.docs import releases

print('Estou dentro do iaEditais/events/events.py', Settings().BROKER_URL)
router = RabbitRouter(url=Settings().BROKER_URL)

router.include_router(releases.router)
