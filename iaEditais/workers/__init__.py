from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.workers.docs import releases

router = RabbitRouter()


router.include_router(releases.router)
