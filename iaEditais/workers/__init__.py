from faststream.rabbit.fastapi import RabbitRouter

from iaEditais.workers.docs import releases
from iaEditais.workers.evaluation import test_runs as evaluation_test_runs

router = RabbitRouter()


router.include_router(releases.router)
router.include_router(evaluation_test_runs.router)
