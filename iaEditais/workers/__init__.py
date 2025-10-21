from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.workers.docs import releases

router = RabbitRouter('amqp://guest:guest@localhost:5673/')

router.include_router(releases.router)
