from fastapi import FastAPI
from iaEditais.config import Settings
from iaEditais.routers.SourceRouter import router as source_router
from iaEditais.routers.Taxonomy.GuidelineRouter import (
    router as guideline_router,
)
from iaEditais.routers.Taxonomy.EvaluateRouter import (
    router as evaluate_router,
)
from iaEditais.routers.DocumentRouter import (
    router as document_router,
)

app = FastAPI(
    root_path=Settings().ROOT_PATH,
    title='IA Editais',
)

app.include_router(source_router, tags=['Source'])
app.include_router(guideline_router, tags=['Guideline'])
app.include_router(evaluate_router, tags=['Evaluation'])
app.include_router(document_router, tags=['Document'])


@app.get('/')
def read_root():
    return {'message': 'Olá Mundo!'}
