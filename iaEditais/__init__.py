from fastapi import FastAPI
from iaEditais.config import Settings
from iaEditais.routers.SourceRouter import router as source_router
from iaEditais.routers.Taxonomy.GuidelinesRouter import (
    router as guidelines_router,
)
from iaEditais.routers.Taxonomy.EvaluationsRouter import (
    router as evaluations_router,
)

app = FastAPI(root_path=Settings().ROOT_PATH)

app.include_router(source_router, tags=['Source'])
app.include_router(guidelines_router, tags=['Taxonomy', 'Guidelines'])
app.include_router(evaluations_router, tags=['Taxonomy', 'Evaluations'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
